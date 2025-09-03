import { useMutation, useQueryClient } from "@tanstack/react-query";
import { SecretsService } from "#/api/secrets-service";
import { IntegrationCreateData, IntegrationUpdateData, IntegrationApiPayload } from "#/types/settings";

export const useCreateIntegration = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (integration: IntegrationApiPayload) => 
      SecretsService.createIntegration(integration),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["integrations"] });
      await queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });
};

export const useUpdateIntegration = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, integration }: { id: string; integration: IntegrationUpdateData }) => 
      SecretsService.updateIntegration(id, integration),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["integrations"] });
      await queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });
};

export const useDeleteIntegration = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (integrationId: string) => 
      SecretsService.deleteIntegration(integrationId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["integrations"] });
      await queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });
};