import { useQuery } from "@tanstack/react-query";
import { SecretsService } from "#/api/secrets-service";

export const useIntegrations = () => {
  return useQuery({
    queryKey: ["integrations"],
    queryFn: SecretsService.getIntegrations,
  });
};