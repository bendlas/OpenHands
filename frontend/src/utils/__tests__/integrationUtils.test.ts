import { describe, it, expect } from 'vitest';
import { generateIntegrationId } from '../integrationUtils';

describe('generateIntegrationId', () => {
  it('should generate a basic ID from a simple name', () => {
    const result = generateIntegrationId('Personal GitHub', []);
    expect(result).toBe('personal-github');
  });

  it('should handle special characters', () => {
    const result = generateIntegrationId('My@Company#GitLab!', []);
    expect(result).toBe('my-company-gitlab');
  });

  it('should handle leading and trailing hyphens', () => {
    const result = generateIntegrationId('--test--', []);
    expect(result).toBe('test');
  });

  it('should fall back to "integration" for names with no alphanumeric chars', () => {
    const result = generateIntegrationId('!@#$%', []);
    expect(result).toBe('integration');
  });

  it('should resolve conflicts by appending numbers', () => {
    const existingIds = ['github-personal', 'github-personal-1'];
    const result = generateIntegrationId('GitHub Personal', existingIds);
    expect(result).toBe('github-personal-2');
  });

  it('should not conflict with empty existing IDs', () => {
    const result = generateIntegrationId('Work GitLab', []);
    expect(result).toBe('work-gitlab');
  });

  it('should handle names that are already ID-like', () => {
    const result = generateIntegrationId('work-gitlab', []);
    expect(result).toBe('work-gitlab');
  });

  it('should handle complex conflict resolution', () => {
    const existingIds = ['test', 'test-1', 'test-2', 'test-4'];
    const result = generateIntegrationId('Test', existingIds);
    expect(result).toBe('test-3'); // Should find the first available number
  });

  it('should handle spaces and underscores', () => {
    const result = generateIntegrationId('My_Company GitHub', []);
    expect(result).toBe('my-company-github');
  });

  it('should handle numbers in names', () => {
    const result = generateIntegrationId('GitHub Enterprise 2024', []);
    expect(result).toBe('github-enterprise-2024');
  });
});