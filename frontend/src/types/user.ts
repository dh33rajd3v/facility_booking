import type { RateCategory } from "./facility";

export interface Me {
  id: number;
  email: string;
  name: string;
  rate_category: RateCategory | null;
  is_iit: boolean;
  needs_category: boolean;
  csrf_token: string;
}

export interface AuthConfig {
  google_enabled: boolean;
  dev_login_enabled: boolean;
}
