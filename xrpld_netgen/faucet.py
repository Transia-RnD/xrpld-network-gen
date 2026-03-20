#!/usr/bin/env python
# coding: utf-8

import json


def generate_faucet_package_json() -> str:
    """Generate package.json for the faucet service."""
    package = {
        "name": "xrpld-faucet",
        "version": "1.0.0",
        "description": "Faucet service for XRPLD local networks",
        "main": "dist/server.js",
        "scripts": {
            "start": "tsx src/server.ts",
            "test": "jest",
            "build": "tsc",
        },
        "dependencies": {
            "xrpl": "^4.0.0",
            "hono": "^4.0.0",
            "@hono/node-server": "^1.0.0",
        },
        "devDependencies": {
            "typescript": "^5.0.0",
            "tsx": "^4.21.0",
            "jest": "^29.0.0",
            "ts-jest": "^29.0.0",
            "@types/jest": "^29.0.0",
            "@types/node": "^20.0.0",
        },
    }
    return json.dumps(package, indent=2) + "\n"


def generate_faucet_tsconfig() -> str:
    """Generate tsconfig.json for the faucet service."""
    tsconfig = {
        "compilerOptions": {
            "target": "ES2020",
            "module": "commonjs",
            "outDir": "./dist",
            "rootDir": "./src",
            "strict": True,
            "esModuleInterop": True,
            "skipLibCheck": True,
        },
        "include": ["src/**/*"],
        "exclude": ["node_modules", "dist"],
    }
    return json.dumps(tsconfig, indent=2) + "\n"


def generate_faucet_server() -> str:
    """Generate the main faucet server TypeScript source."""
    return '''\
import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { Client, Wallet, dropsToXrp, xrpToDrops, ECDSA } from "xrpl";

const RATE_LIMIT_MS = parseInt(process.env.RATE_LIMIT_MS || "10000");
const DEFAULT_AMOUNT = process.env.DEFAULT_XRP_AMOUNT || "1000";
const XRPLD_WS_URL = process.env.XRPLD_WS_URL || "ws://localhost:6006";
const PORT = parseInt(process.env.PORT || "8080");

const genesisWallet = Wallet.fromSecret('snoPBrXtMeMyMHUVTgbuqAfg1SUTb', { algorithm: ECDSA.secp256k1 });

let faucetWallet: Wallet;

const rateLimitMap = new Map<string, number>();

const app = new Hono();

async function connectWithRetry(client: Client): Promise<void> {
  const maxRetries = 60;
  for (let i = 0; i < maxRetries; i++) {
    try {
      await client.connect();
      console.log("Connected to xrpld");
      return;
    } catch (err) {
      console.log(
        `Connection attempt ${i + 1}/${maxRetries} failed, retrying in 5s...`
      );
      await new Promise((resolve) => setTimeout(resolve, 5000));
    }
  }
  throw new Error("Failed to connect to xrpld after maximum retries");
}

async function initFaucetWallet(client: Client): Promise<void> {
  const xrpBalance = await client.getXrpBalance(genesisWallet.address);

  const balanceDrops = BigInt(xrpToDrops(xrpBalance));
  const fundingDrops = (balanceDrops * BigInt(90)) / BigInt(100);

  console.log(`Genesis wallet address: ${genesisWallet.address}`);
  faucetWallet = Wallet.generate();
  console.log(`Faucet wallet address: ${faucetWallet.address}`);

  const payment = {
    TransactionType: "Payment" as const,
    Account: genesisWallet.address,
    Destination: faucetWallet.address,
    Amount: fundingDrops.toString(),
  };

  const result = await client.submitAndWait(payment, {
    wallet: genesisWallet,
  });
  console.log(
    `Funded faucet wallet: ${dropsToXrp(fundingDrops.toString())} XRP`
  );
  console.log(`Transaction result: ${JSON.stringify(result.result, null, 2)}`);
}

app.get("/health", (c) => {
  return c.json({
    status: "ok",
    faucetAddress: faucetWallet?.address,
  });
});

app.post("/accounts", async (c) => {
  try {
    const ip = c.req.header("x-forwarded-for") || "unknown";
    const now = Date.now();
    const lastRequest = rateLimitMap.get(ip);

    if (lastRequest && now - lastRequest < RATE_LIMIT_MS) {
      return c.json(
        { error: "Rate limit exceeded. Please wait before requesting again." },
        429
      );
    }
    rateLimitMap.set(ip, now);

    const body = await c.req.json().catch(() => ({}));
    const { destination, xrpAmount } = body as {
      destination?: string;
      xrpAmount?: string;
    };

    const amount = xrpAmount || DEFAULT_AMOUNT;
    let targetAddress: string;
    let secret: string | undefined;

    if (destination) {
      if (
        !destination.startsWith("r") ||
        destination.length < 25 ||
        destination.length > 35
      ) {
        return c.json({ error: "Invalid destination address" }, 400);
      }
      targetAddress = destination;
    } else {
      const newWallet = Wallet.generate();
      targetAddress = newWallet.address;
      secret = newWallet.seed;
    }

    const client = new Client(XRPLD_WS_URL);
    client.apiVersion = 1;
    await client.connect();

    try {
      const payment = {
        TransactionType: "Payment" as const,
        Account: faucetWallet.address,
        Destination: targetAddress,
        Amount: xrpToDrops(amount),
      };

      await client.submit(payment, { wallet: faucetWallet });

      const xrpBalance = await client.getXrpBalance(targetAddress, { ledger_index: 'current' });

      const response: Record<string, unknown> = {
        account: {
          address: targetAddress,
          classicAddress: targetAddress,
          ...(secret ? { secret } : {}),
        },
        amount: parseInt(amount),
        balance: xrpBalance,
      };

      return c.json(response);
    } finally {
      await client.disconnect();
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error(`Error funding account: ${message}`);
    return c.json({ error: `Failed to fund account: ${message}` }, 500);
  }
});

async function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main(): Promise<void> {
  while (true) {
    const client = new Client(XRPLD_WS_URL);
    client.apiVersion = 1;
    try {
      await connectWithRetry(client);
      await initFaucetWallet(client);
      break;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error";
      console.error(`Fatal error: ${message}`);
      await wait(5000);
    } finally {
      await client.disconnect();
    }
  }
}

main();
serve({ fetch: app.fetch, port: PORT });

export { app };
'''


def generate_faucet_dockerfile() -> str:
    """Generate Dockerfile for the faucet service."""
    return """\
FROM node:20-slim

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 8080

CMD ["npx", "tsx", "src/server.ts"]
"""


def generate_faucet_test() -> str:
    """Generate Jest test code for the faucet server."""
    return '''\
import { app } from "./server";

jest.mock("xrpl", () => {
  const mockClient = {
    connect: jest.fn().mockResolvedValue(undefined),
    disconnect: jest.fn().mockResolvedValue(undefined),
    getBalances: jest.fn().mockResolvedValue([
      { currency: "XRP", value: "1000" },
    ]),
    submitAndWait: jest.fn().mockResolvedValue({
      result: { meta: "tesSUCCESS" },
    }),
  };

  return {
    Client: jest.fn(() => mockClient),
    Wallet: {
      fromSeed: jest.fn(() => ({
        address: "rGenesisAddress",
        seed: "sGenesisSecret",
      })),
      generate: jest.fn(() => ({
        address: "rNewTestAddress",
        seed: "sNewTestSecret",
        classicAddress: "rNewTestAddress",
      })),
    },
    dropsToXrp: jest.fn((drops: string) =>
      (parseInt(drops) / 1000000).toString()
    ),
    xrpToDrops: jest.fn((xrp: string) =>
      (parseFloat(xrp) * 1000000).toString()
    ),
  };
});

describe("Faucet Server", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("GET /health", () => {
    it("should return status ok", async () => {
      const res = await app.request("/health");
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.status).toBe("ok");
    });
  });

  describe("POST /accounts", () => {
    it("should create a new account", async () => {
      const res = await app.request("/accounts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-forwarded-for": "10.0.0.1",
        },
        body: JSON.stringify({}),
      });
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.account).toBeDefined();
      expect(body.account.address).toBeDefined();
      expect(body.account.secret).toBeDefined();
      expect(body.amount).toBeDefined();
    });

    it("should fund destination without returning secret", async () => {
      const res = await app.request("/accounts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-forwarded-for": "10.0.0.2",
        },
        body: JSON.stringify({ destination: "rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe" }),
      });
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.account).toBeDefined();
      expect(body.account.address).toBe("rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe");
      expect(body.account.secret).toBeUndefined();
    });

    it("should accept custom xrpAmount", async () => {
      const res = await app.request("/accounts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-forwarded-for": "10.0.0.3",
        },
        body: JSON.stringify({ xrpAmount: "500" }),
      });
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.amount).toBe(500);
    });

    it("should return 429 on rapid requests", async () => {
      const headers = {
        "Content-Type": "application/json",
        "x-forwarded-for": "10.0.0.4",
      };

      const res1 = await app.request("/accounts", {
        method: "POST",
        headers,
        body: JSON.stringify({}),
      });
      expect(res1.status).toBe(200);

      const res2 = await app.request("/accounts", {
        method: "POST",
        headers,
        body: JSON.stringify({}),
      });
      expect(res2.status).toBe(429);
    });

    it("should return 400 for invalid destination address", async () => {
      const res = await app.request("/accounts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-forwarded-for": "10.0.0.5",
        },
        body: JSON.stringify({ destination: "invalid_address" }),
      });
      expect(res.status).toBe(400);
      const body = await res.json();
      expect(body.error).toBeDefined();
    });
  });
});
'''


def generate_faucet_jest_config() -> str:
    """Generate Jest configuration for the faucet service."""
    return """\
module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  roots: ["<rootDir>/src"],
};
"""
