/**
 * Generate a unique integration ID based on name and existing IDs
 */
export function generateIntegrationId(name: string, existingIds: string[]): string {
  // Basic sanitization: lowercase, replace spaces/special chars with hyphens
  const baseId = name
    .toLowerCase()
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-+|-+$/g, ""); // trim leading/trailing hyphens

  if (!baseId) {
    // Fallback if name has no alphanumeric characters
    return "integration";
  }

  // Try the base ID first
  let candidateId = baseId;
  let counter = 1;

  // If ID already exists, append a number
  while (existingIds.indexOf(candidateId) !== -1) {
    candidateId = `${baseId}-${counter}`;
    counter++;
  }

  return candidateId;
}