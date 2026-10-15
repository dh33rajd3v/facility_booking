import { apiGet } from "./client";
import type { FacilityList, Health } from "../types/facility";

export function fetchFacilities(signal?: AbortSignal): Promise<FacilityList> {
  return apiGet<FacilityList>("/facilities?active=true", { signal });
}

export function fetchHealth(signal?: AbortSignal): Promise<Health> {
  return apiGet<Health>("/health", { signal });
}
