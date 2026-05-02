export type FrequencyType = "daily" | "weekly" | "every_n_days";

export interface Newsletter {
  id: number;
  user_id: string;
  email: string;
  title: string;
  themes: string[];
  frequency_type: FrequencyType;
  frequency_interval_days: number;
  is_active: boolean;
  next_run_at?: string;
  last_sent_at?: string | null;
  generated_title?: string | null;
  generated_text_content?: string | null;
}

export interface NewsletterPayload {
  email: string;
  title: string;
  themes: string[];
  frequency_type: FrequencyType;
  frequency_interval_days: number;
}
