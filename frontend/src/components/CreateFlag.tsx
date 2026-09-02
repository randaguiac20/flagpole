// Create a flag. Spec: 002-flagpole-web FR-015 (US3-5, US3-6).
import { useState } from "react";

interface CreateFlagProps {
  canEdit: boolean;
  onCreate: (key: string, description: string) => Promise<void>;
}

export function CreateFlag({ canEdit, onCreate }: CreateFlagProps) {
  const [key, setKey] = useState("");
  const [description, setDescription] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      await onCreate(key, description);
      setKey("");
      setDescription("");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "could not create the flag");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="create-flag" onSubmit={submit}>
      <label>
        Key
        <input
          data-testid="create-key"
          value={key}
          disabled={!canEdit || busy}
          onChange={(e) => setKey(e.target.value)}
          placeholder="new_flag_key"
        />
      </label>
      <label>
        Description
        <input
          data-testid="create-description"
          value={description}
          disabled={!canEdit || busy}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>
      <button type="submit" data-testid="create-submit" disabled={!canEdit || busy || key === ""}>
        Create
      </button>
      {message ? (
        <span className="error" role="alert" data-testid="create-error">
          {message}
        </span>
      ) : null}
    </form>
  );
}
