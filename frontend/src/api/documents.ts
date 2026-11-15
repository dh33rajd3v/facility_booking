import type { BookingRequest } from "../types/request";
import { API_BASE_URL, apiRequest } from "./client";

export const MAX_UPLOAD_MB = 5;
export const ACCEPTED_TYPES = ".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png";

/** Attach (or replace) the Govt./PSU proof document of a draft or returned request. */
export function uploadRequestDocument(requestId: number, file: File): Promise<BookingRequest> {
  const form = new FormData();
  form.append("file", file);
  return apiRequest<BookingRequest>("POST", `/requests/${requestId}/document`, form);
}

/** Links that open the document in a new tab; the session cookie proves who is asking. */
export const requestDocumentUrl = (requestId: number) => `${API_BASE_URL}/requests/${requestId}/document`;
export const staffDocumentUrl = (requestId: number) => `${API_BASE_URL}/workflow/requests/${requestId}/document`;

/** Client-side check before uploading (the server checks again, by the file's contents). */
export function checkProofFile(file: File | null): string | null {
  if (!file) return "Choose a proof document to upload.";
  if (file.size === 0) return "The file is empty.";
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `The file is larger than ${MAX_UPLOAD_MB} MB.`;
  if (!/\.(pdf|jpe?g|png)$/i.test(file.name)) return "Upload a PDF, JPG or PNG file.";
  return null;
}

export function fileSize(bytes: number): string {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}
