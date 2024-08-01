/**
 * Download a specific commit hash from a GitHub repository.
*
* @param server - The owner of the repository (username or organization)
* @param version - The name of the repository
* @return The commit hash
*/
async function getCommitHashFromServerVersion(server: string, version: string): Promise<string> {

  // Send a GET request to the URL to download the file
  const response = await fetch(`${server}/${version}.releaseinfo`);

  // Check if the request was successful
  if (response.status === 200) {
    // Read the contents of the file
    const releaseInfo = await response.text();

    // Use a regular expression to find the commit hash
    const match = releaseInfo.match(/commit (\w+)/);

    // If a match is found, return the commit hash
    if (match) {
      return match[1];
    } else {
      throw new Error("Commit hash not found in the release info.");
    }
  } else {
    // If the request was not successful, throw an error
    throw new Error(`HTTP error: ${response.status}`);
  }
}

/**
 * Download a specific file from a GitHub repository at a given commit hash or tag.
*
* @param owner - The owner of the repository (username or organization)
* @param repo - The name of the repository
* @param commitHashOrTag - The commit hash or version tag
* @param filePath - The path to the file in the repository
* @return The content of the file
*/
async function downloadFileAtCommitOrTag(owner: string, repo: string, commitHashOrTag: string, filePath: string): Promise<string> {
  // Construct the raw content URL
  const url = `https://raw.githubusercontent.com/${owner}/${repo}/${commitHashOrTag}/${filePath}`;

  // Send a GET request to the URL
  const response = await fetch(url);
  if (response.status !== 200) {
    throw new Error(`HTTP error: ${response.status}`);
  }

  // Return the content of the file
  return await response.text();
}

export { getCommitHashFromServerVersion, downloadFileAtCommitOrTag };
