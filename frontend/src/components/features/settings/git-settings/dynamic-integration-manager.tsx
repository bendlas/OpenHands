import React, { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Integration, IntegrationCreateData } from "#/types/settings";
import { useIntegrations } from "#/hooks/query/use-integrations";
import {
  useCreateIntegration,
  useDeleteIntegration,
  useUpdateIntegration,
} from "#/hooks/mutation/use-integration-mutations";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { retrieveAxiosErrorMessage } from "#/utils/retrieve-axios-error-message";
import { I18nKey } from "#/i18n/declaration";
import { generateIntegrationId } from "#/utils/integrationUtils";

// Supported provider types
const PROVIDER_TYPES = [
  { value: "github", label: "GitHub" },
  { value: "gitlab", label: "GitLab" },
  { value: "bitbucket", label: "Bitbucket" },
  { value: "gitea", label: "Gitea" },
  { value: "forgejo", label: "Forgejo" },
  { value: "sourcehut", label: "SourceHut" },
];

interface EditIntegrationFormProps {
  integration: Integration;
  onCancel: () => void;
  onSuccess: () => void;
}

const EditIntegrationForm: React.FC<EditIntegrationFormProps> = ({
  integration,
  onCancel,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const { mutate: updateIntegration, isPending } = useUpdateIntegration();
  const { data: integrations = [] } = useIntegrations();

  const [formData, setFormData] = useState<IntegrationCreateData>({
    id: integration.id,
    provider_type: integration.provider_type,
    name: integration.name,
    host: integration.host || "",
    token: "", // Don't pre-fill token for security
    user_id: integration.user_id || "",
  });

  const [showCustomId, setShowCustomId] = useState(true); // Always show custom for edit

  // Generate preview ID based on current name (for reference)
  const existingIds = integrations
    .filter((int) => int.id !== integration.id) // Exclude current integration
    .map((int) => int.id);
  const previewId = useMemo(() => {
    if (!formData.name.trim()) return "";
    return generateIntegrationId(formData.name, existingIds);
  }, [formData.name, existingIds]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name) {
      displayErrorToast("Name is required");
      return;
    }

    if (!formData.id) {
      displayErrorToast("ID is required");
      return;
    }

    // Update the integration
    updateIntegration(
      { id: integration.id, integration: formData },
      {
        onSuccess: () => {
          displaySuccessToast(
            `Integration "${formData.name}" updated successfully`,
          );
          onSuccess();
        },
        onError: (error) => {
          const errorMessage = retrieveAxiosErrorMessage(error);
          displayErrorToast(errorMessage || "Failed to update integration");
        },
      },
    );
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 bg-gray-800 p-4 rounded-lg border-2 border-blue-600"
    >
      <h3 className="text-lg font-medium text-white">Edit Integration</h3>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Display Name *
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="e.g., GitHub Personal"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Integration ID *
          </label>
          <div className="relative">
            <input
              type="text"
              value={formData.id || ""}
              onChange={(e) =>
                setFormData({ ...formData, id: e.target.value })
              }
              placeholder="e.g., github-personal"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Current ID. Suggested: {previewId}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Provider Type *
          </label>
          <select
            value={formData.provider_type}
            onChange={(e) =>
              setFormData({ ...formData, provider_type: e.target.value })
            }
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {PROVIDER_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Host (optional)
          </label>
          <input
            type="text"
            value={formData.host || ""}
            onChange={(e) =>
              setFormData({ ...formData, host: e.target.value || null })
            }
            placeholder="e.g., github.enterprise.com"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-300 mb-1">
            API Token (leave empty to keep current)
          </label>
          <input
            type="password"
            value={formData.token || ""}
            onChange={(e) =>
              setFormData({ ...formData, token: e.target.value || null })
            }
            placeholder="Enter new API token or leave empty to keep current"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-300 mb-1">
            User ID (optional)
          </label>
          <input
            type="text"
            value={formData.user_id || ""}
            onChange={(e) =>
              setFormData({ ...formData, user_id: e.target.value || null })
            }
            placeholder="Your user ID for this provider"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex justify-end space-x-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-gray-300 hover:text-white transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isPending ? "Updating..." : "Update Integration"}
        </button>
      </div>
    </form>
  );
};

interface AddIntegrationFormProps {
  onCancel: () => void;
  onSuccess: () => void;
}

const AddIntegrationForm: React.FC<AddIntegrationFormProps> = ({
  onCancel,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const { mutate: createIntegration, isPending } = useCreateIntegration();
  const { data: integrations = [] } = useIntegrations();

  const [formData, setFormData] = useState<IntegrationCreateData>({
    provider_type: "github",
    name: "",
    host: "",
    token: "",
    user_id: "",
  });

  const [showCustomId, setShowCustomId] = useState(false);

  // Generate preview ID based on current name
  const existingIds = integrations.map((integration) => integration.id);
  const previewId = useMemo(() => {
    if (!formData.name.trim()) return "";
    return generateIntegrationId(formData.name, existingIds);
  }, [formData.name, existingIds]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name) {
      displayErrorToast("Name is required");
      return;
    }

    // Require token for certain provider types
    const requiredTokenProviders = ['github', 'gitlab', 'bitbucket'];
    if (requiredTokenProviders.includes(formData.provider_type) && !formData.token) {
      displayErrorToast(`API token is required for ${formData.provider_type} integrations`);
      return;
    }

    // Always provide an ID - either custom or auto-generated
    const integrationId = showCustomId && formData.id 
      ? formData.id 
      : previewId;
    
    if (!integrationId) {
      displayErrorToast("Unable to generate integration ID");
      return;
    }

    const submissionData = { 
      ...formData,
      id: integrationId
    };

    createIntegration(submissionData, {
      onSuccess: () => {
        displaySuccessToast(
          `Integration "${formData.name}" added successfully`,
        );
        onSuccess();
      },
      onError: (error) => {
        const errorMessage = retrieveAxiosErrorMessage(error);
        displayErrorToast(errorMessage || "Failed to add integration");
      },
    });
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 bg-gray-800 p-4 rounded-lg"
    >
      <h3 className="text-lg font-medium text-white">Add New Integration</h3>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Display Name *
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="e.g., GitHub Personal"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Integration ID
          </label>
          {!showCustomId ? (
            <div className="relative">
              <div className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-md text-gray-300 text-sm">
                {previewId || "Will be auto-generated..."}
              </div>
              <button
                type="button"
                onClick={() => setShowCustomId(true)}
                className="absolute right-2 top-1/2 transform -translate-y-1/2 text-xs text-blue-400 hover:text-blue-300"
              >
                Custom
              </button>
            </div>
          ) : (
            <div className="relative">
              <input
                type="text"
                value={formData.id || ""}
                onChange={(e) =>
                  setFormData({ ...formData, id: e.target.value })
                }
                placeholder="e.g., github-personal"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={() => {
                  setShowCustomId(false);
                  setFormData({ ...formData, id: undefined });
                }}
                className="absolute right-2 top-1/2 transform -translate-y-1/2 text-xs text-gray-400 hover:text-gray-300"
              >
                Auto
              </button>
            </div>
          )}
          <p className="text-xs text-gray-400 mt-1">
            {!showCustomId
              ? "Auto-generated from display name. Click 'Custom' to override."
              : "Enter custom ID or click 'Auto' to use auto-generated."}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Provider Type *
          </label>
          <select
            value={formData.provider_type}
            onChange={(e) =>
              setFormData({ ...formData, provider_type: e.target.value })
            }
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {PROVIDER_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Host (optional)
          </label>
          <input
            type="text"
            value={formData.host || ""}
            onChange={(e) =>
              setFormData({ ...formData, host: e.target.value || null })
            }
            placeholder="e.g., github.enterprise.com"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-300 mb-1">
            API Token *
          </label>
          <input
            type="password"
            value={formData.token || ""}
            onChange={(e) =>
              setFormData({ ...formData, token: e.target.value || null })
            }
            placeholder="Enter your API token (required)"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>

        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-300 mb-1">
            User ID (optional)
          </label>
          <input
            type="text"
            value={formData.user_id || ""}
            onChange={(e) =>
              setFormData({ ...formData, user_id: e.target.value || null })
            }
            placeholder="Your user ID for this provider"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex justify-end space-x-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-gray-300 hover:text-white transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isPending ? "Adding..." : "Add Integration"}
        </button>
      </div>
    </form>
  );
};

interface IntegrationItemProps {
  integration: Integration;
  onEdit: (integration: Integration) => void;
  onDelete: (integrationId: string) => void;
}

const IntegrationItem: React.FC<IntegrationItemProps> = ({
  integration,
  onEdit,
  onDelete,
}) => {
  const providerLabel =
    PROVIDER_TYPES.find((p) => p.value === integration.provider_type)?.label ||
    integration.provider_type;

  return (
    <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h4 className="text-lg font-medium text-white">{integration.name}</h4>
          <p className="text-gray-400 text-sm">
            {providerLabel} • ID: {integration.id}
          </p>
          {integration.host && (
            <p className="text-gray-400 text-sm">Host: {integration.host}</p>
          )}
          <p className="text-gray-400 text-sm">
            Token:{" "}
            {integration.has_token ? "✅ Configured" : "❌ Not configured"}
          </p>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={() => onEdit(integration)}
            className="px-3 py-1 text-blue-400 hover:text-blue-300 text-sm transition-colors"
          >
            Edit
          </button>
          <button
            onClick={() => onDelete(integration.id)}
            className="px-3 py-1 text-red-400 hover:text-red-300 text-sm transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
};

export const DynamicIntegrationManager: React.FC = () => {
  const { data: integrations, isLoading } = useIntegrations();
  const { mutate: deleteIntegration } = useDeleteIntegration();

  const [showAddForm, setShowAddForm] = useState(false);
  const [editingIntegration, setEditingIntegration] = useState<Integration | null>(null);

  const handleDelete = (integrationId: string) => {
    // eslint-disable-next-line no-restricted-globals, no-alert
    if (confirm("Are you sure you want to delete this integration?")) {
      deleteIntegration(integrationId, {
        onSuccess: () => {
          displaySuccessToast("Integration deleted successfully");
        },
        onError: (error) => {
          const errorMessage = retrieveAxiosErrorMessage(error);
          displayErrorToast(errorMessage || "Failed to delete integration");
        },
      });
    }
  };

  const handleEdit = (integration: Integration) => {
    setEditingIntegration(integration);
    setShowAddForm(false); // Close add form if open
  };

  const handleEditCancel = () => {
    setEditingIntegration(null);
  };

  const handleEditSuccess = () => {
    setEditingIntegration(null);
  };

  if (isLoading) {
    return (
      <div className="p-4">
        <div className="text-gray-400">Loading integrations...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        {/* eslint-disable-next-line i18next/no-literal-string */}
        <h3 className="text-xl font-medium text-white">
          Git Provider Integrations
        </h3>
        <button
          type="button"
          onClick={() => {
            setShowAddForm(true);
            setEditingIntegration(null); // Close edit form if open
          }}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          {/* eslint-disable-next-line i18next/no-literal-string */}
          Add Integration
        </button>
      </div>

      {showAddForm && (
        <AddIntegrationForm
          onCancel={() => setShowAddForm(false)}
          onSuccess={() => setShowAddForm(false)}
        />
      )}

      {editingIntegration && (
        <EditIntegrationForm
          integration={editingIntegration}
          onCancel={handleEditCancel}
          onSuccess={handleEditSuccess}
        />
      )}

      {integrations && integrations.length > 0 ? (
        <div className="space-y-3">
          {integrations.map((integration) => (
            <IntegrationItem
              key={integration.id}
              integration={integration}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-400">
          {/* eslint-disable-next-line i18next/no-literal-string */}
          <p>No integrations configured yet.</p>
          {/* eslint-disable-next-line i18next/no-literal-string */}
          <p className="text-sm">Add your first integration to get started.</p>
        </div>
      )}
    </div>
  );
};
