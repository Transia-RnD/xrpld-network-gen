import * as fs from 'fs';
import * as crypto from 'crypto';
import { downloadFileAtCommitOrTag } from './github';
import path from 'path';

interface Amendments {
  [key: string]: {
    supported: boolean;
    default_vote: boolean;
  };
}

const basedir = process.cwd()
const srcDir = path.join(basedir, 'src')

function readJson(filePath: string): any {
  const data = fs.readFileSync(filePath, 'utf-8');
  return JSON.parse(data);
}

function convertToListOfHashes(features: Record<string, any>): string[] {
  return Object.keys(features).map(key =>
    crypto.createHash('sha512').update(key).digest('hex').toUpperCase().slice(0, 64)
  );
}

export async  function updateAmendments(features: Record<string, any>, xrplProtocol: string) {
  const jsonText = fs.readFileSync(`${srcDir}/genesis.${xrplProtocol}.json`, 'utf-8')
  const jsonDict = JSON.parse(jsonText);

  const newAmendments: string[] = convertToListOfHashes(features);

  for (const dct of jsonDict['ledger']['accountState']) {
    if ('Amendments' in dct) {
      dct['Amendments'] = newAmendments;
    }
  }

  return jsonDict;
}

export function parseRippledAmendments(lines: string[]): Record<string, string> {
  const amendments: Amendments = {};
  const registerFeatureRegex = /REGISTER_FEATURE\((.*?),/;
  const registerFixRegex = /REGISTER_FIX\)?.*?\((.*?),/;
  const supportedRegex = /Supported::(.*),/;
  const defaultVoteRegex = /DefaultVote::(.*),/;

  for (const line of lines) {
    let amendmentName = '';
    if (registerFixRegex.test(line)) {
      amendmentName = registerFixRegex.exec(line)?.[1] || '';
    } else if (registerFeatureRegex.test(line)) {
      amendmentName = registerFeatureRegex.exec(line)?.[1] || '';
    }

    const supported = supportedRegex.exec(line)?.[1] || 'no';
    const defaultVote = defaultVoteRegex.exec(line)?.[1] || 'no';

    amendments[amendmentName] = {
      supported: supported === 'yes',
      default_vote: defaultVote === 'yes',
    };
  }

  return Object.fromEntries(
    Object.entries(amendments)
      .filter(([, v]) => v.supported)
      .map(([k]) => [k, crypto.createHash('sha512').update(k).digest('hex').toUpperCase().slice(0, 64)])
  );
}

export function getFeatureLinesFromPath(filePath: string): string[] {
  const content = fs.readFileSync(filePath, 'utf-8');
  return content.split('\n');
}

export function getFeatureLinesFromContent(content: string): string[] {
  return content.split('\n');
}
