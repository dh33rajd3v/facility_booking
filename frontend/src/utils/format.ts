import type { FacilityGroup, RateCategory, Section, SlotUnit } from "../types/facility";

const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export function formatInr(amount: number): string {
  return amount === 0 ? "No charges" : inr.format(amount);
}

export const CATEGORY_LABELS: Record<RateCategory, string> = {
  PRIVATE: "Private / outside agencies",
  GOVT: "Govt. / Semi Govt. / PSU",
  IIT: "IIT Ropar",
};

export const CATEGORY_SHORT: Record<RateCategory, string> = {
  PRIVATE: "Private",
  GOVT: "Govt / PSU",
  IIT: "IIT Ropar",
};

export const UNIT_LABELS: Record<SlotUnit, string> = {
  FULL_DAY: "Full day",
  HALF_DAY: "Half day",
  PER_DAY: "Per day",
  THREE_HOUR: "3-hour slot",
};

export const GROUP_LABELS: Record<FacilityGroup, string> = {
  LHC: "Lecture Hall Complex",
  AUDITORIUM: "Auditorium",
  SPORTS: "Sports grounds",
};

export const SECTION_LABELS: Record<Section, string> = {
  ACADEMIC: "Academic section",
  SPORTS: "Sports section",
};
