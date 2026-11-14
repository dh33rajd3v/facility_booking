import { useRef, useState } from "react";
import { errorMessage } from "../api/client";
import {
  ACCEPTED_TYPES,
  MAX_UPLOAD_MB,
  checkProofFile,
  fileSize,
  requestDocumentUrl,
  uploadRequestDocument,
} from "../api/documents";
import type { BookingRequest } from "../types/request";
import { formatDateTime } from "../utils/format";
import "../styles/documents.css";

interface Props {
  request: BookingRequest;
  /** Called with the updated request after an upload. Leave out to show the document read-only. */
  onUploaded?: (request: BookingRequest) => void;
}

/**
 * The Govt./PSU proof document of a request. Requests at that rate can't be submitted without one;
 * Facilities checks it and returns the request if it isn't acceptable.
 */
export function ProofDocument({ request, onUploaded }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  if (!request.needs_document && !request.document) return null;
  const doc = request.document ?? null;
  const canUpload = Boolean(onUploaded) && request.editable && request.needs_document;

  async function upload() {
    const problem = checkProofFile(file);
    if (problem) {
      setError(problem);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const updated = await uploadRequestDocument(request.id, file as File);
      setFile(null);
      if (input.current) input.current.value = "";
      onUploaded?.(updated);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`panel proof${!doc && request.needs_document ? " proof--missing" : ""}`}>
      <h2 id={`proof-heading-${request.id}`}>Govt./PSU proof document</h2>
      <p className="muted">
        Requests at the Govt./PSU rate need proof that your organisation is a government body or PSU, for example
        an authorisation letter on letterhead or an official ID card. Facilities checks it before forwarding your
        request.
      </p>
      {doc ? (
        <p className="proof__file">
          <a href={requestDocumentUrl(request.id)} target="_blank" rel="noreferrer">
            {doc.original_filename}
          </a>{" "}
          <span className="muted">
            {fileSize(doc.size_bytes)} · uploaded {formatDateTime(doc.uploaded_at)}
          </span>
        </p>
      ) : (
        request.needs_document && (
          <p className="alert alert--warning">No document yet. You need one before you can submit.</p>
        )
      )}
      {canUpload && (
        <div className="upload-field field">
          <label htmlFor={`proof-file-${request.id}`}>{doc ? "Replace the document" : "Proof document"}</label>
          <input
            id={`proof-file-${request.id}`}
            ref={input}
            type="file"
            accept={ACCEPTED_TYPES}
            aria-describedby={`proof-hint-${request.id}`}
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setError(null);
            }}
          />
          <span className="hint" id={`proof-hint-${request.id}`}>
            PDF, JPG or PNG, up to {MAX_UPLOAD_MB} MB.
          </span>
          <span>
            <button type="button" className="button button--secondary" disabled={busy} onClick={() => void upload()}>
              {busy ? "Uploading…" : doc ? "Upload replacement" : "Upload document"}
            </button>
          </span>
        </div>
      )}
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
