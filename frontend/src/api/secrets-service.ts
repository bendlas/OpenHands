import { openHands } from "./open-hands-axios";
import {
  CustomSecret,
  GetSecretsResponse,
  POSTProviderTokens,
} from "./secrets-service.types";
import {
  Integration,
  IntegrationCreateData,
  IntegrationUpdateData,
  IntegrationApiPayload,
  Provider,
  ProviderToken,
} from "#/types/settings";

export class SecretsService {
  static async getSecrets() {
    const { data } = await openHands.get<GetSecretsResponse>("/api/secrets");
    return data.custom_secrets;
  }

  static async createSecret(name: string, value: string, description?: string) {
    const secret: CustomSecret = {
      name,
      value,
      description,
    };

    const { status } = await openHands.post("/api/secrets", secret);
    return status === 201;
  }

  static async updateSecret(id: string, name: string, description?: string) {
    const secret: Omit<CustomSecret, "value"> = {
      name,
      description,
    };

    const { status } = await openHands.put(`/api/secrets/${id}`, secret);
    return status === 200;
  }

  static async deleteSecret(id: string) {
    const { status } = await openHands.delete<boolean>(`/api/secrets/${id}`);
    return status === 200;
  }

  static async addGitProvider(providers: Record<Provider, ProviderToken>) {
    const tokens: POSTProviderTokens = {
      provider_tokens: providers,
    };
    const { data } = await openHands.post<boolean>(
      "/api/add-git-providers",
      tokens,
    );
    return data;
  }

  // New integration management APIs
  static async getIntegrations(): Promise<Integration[]> {
    const { data } = await openHands.get<{ integrations: Integration[] }>(
      "/api/integrations",
    );
    return data.integrations;
  }

  static async createIntegration(
    integration: IntegrationApiPayload,
  ): Promise<boolean> {
    const { status } = await openHands.post("/api/integrations", integration);
    return status === 201;
  }

  static async updateIntegration(
    integrationId: string,
    integration: IntegrationUpdateData,
  ): Promise<boolean> {
    const { status } = await openHands.put(
      `/api/integrations/${integrationId}`,
      integration,
    );
    return status === 200;
  }

  static async deleteIntegration(integrationId: string): Promise<boolean> {
    const { status } = await openHands.delete(
      `/api/integrations/${integrationId}`,
    );
    return status === 200;
  }
}
