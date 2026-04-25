export interface GmailAddressRule {
  keywords?: string[]
  /** include = subject must match a keyword; exclude = skip if subject matches any keyword */
  keyword_mode?: 'include' | 'exclude'
  after_date?: string | null
}

export interface Project {
  id: string
  name: string
  client_type: 'buyer' | 'seller' | 'buyer & seller'
  email_addresses: string[]
  phone?: string
  notes?: string
  drive_folder_id?: string
  drive_folder_name?: string
  /** @deprecated Prefer gmail_address_rules; used when no per-address rule exists */
  gmail_keywords?: string[]
  /** Default for addresses with no saved rule: how global keywords apply to subject */
  gmail_keyword_mode?: 'include' | 'exclude'
  /** Per-address optional subject keywords and/or minimum message date */
  gmail_address_rules?: Record<string, GmailAddressRule>
  last_gmail_sync?: string
  last_drive_sync?: string
  /** anthropic | openai | gemini — server validates against tier + configured keys */
  llm_provider?: string | null
  llm_model?: string | null
  /** When client_type is "buyer & seller", the single listing they are selling */
  sale_property_id?: string | null
  created_at: string
  updated_at?: string
}

export type LlmOptionProvider = {
  id: string
  label: string
  models: { id: string; label: string }[]
}

export type LlmOptionsResponse = {
  providers: LlmOptionProvider[]
  default_provider: string
  subscription_tier?: string
}

export type SubscriptionTier = 'free' | 'trial' | 'pro' | 'max' | 'ultra'

export type AccountEntitlements = {
  subscription_tier: SubscriptionTier
  trial_max_tokens: number
  trial_tokens_used: number
  trial_tokens_remaining: number
  trial_max_days: number
  trial_started_at: string | null
  trial_ends_at: string | null
  pro_included_tokens_per_month: number
  pro_tokens_used: number
  pro_tokens_remaining: number
  pro_billing_month: string | null
  /** True when email is in server ADMIN_EMAILS (unlimited; bypasses caps). */
  is_admin?: boolean
  can_send_chat: boolean
  upgrade_url: string | null
  /** Output tokens count this many times toward caps (input = 1×). */
  quota_output_multiplier?: number
  subscription_status: 'active' | 'past_due' | 'canceled' | 'trialing' | null
  subscription_current_period_end: string | null
  subscription_cancel_at_period_end: boolean
}

export interface Property {
  id: string
  project_id: string
  address: string
  city?: string
  state?: string
  zip_code?: string
  mls_number?: string
  list_price?: number
  beds?: number
  baths?: number
  sqft?: number
  status: string
  notes?: string
}

export interface KeyDate {
  id: string
  transaction_id: string
  label: string
  due_date: string
  completed_at?: string
}

export interface Transaction {
  id: string
  project_id: string
  property_id?: string
  offer_price?: number
  earnest_money?: number
  contingencies: string[]
  status: string
  offer_date?: string
  accepted_date?: string
  close_date?: string
  notes?: string
  created_at: string
  key_dates: KeyDate[]
}

/** Set server-side for ADMIN_EMAILS accounts only; stripped from API for others. */
export type ChatAdminUsage = {
  input_tokens: number
  output_tokens: number
  /** input + output × quota_output_multiplier — matches billing caps. */
  billable_units: number
}

export type ChatReferencedItems = {
  documents?: { id: string; label: string; source?: string }[]
  emails?: { id: string; label: string; date?: string }[]
  doc_fallback?: string
  email_fallback?: string
  triage?: { documents_triage?: boolean; emails_triage?: boolean }
  admin_usage?: ChatAdminUsage
}

export interface ChatMessage {
  id: string
  project_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  referenced_items?: ChatReferencedItems | null
}

export interface Document {
  id: string
  project_id: string
  filename: string
  source: 'upload' | 'drive' | 'gmail'
  drive_file_id?: string
  gmail_message_id?: string
  mime_type?: string
  size_bytes?: number
  created_at: string
  chunk_count: number
}

export interface EmailMessage {
  id: string
  thread_id: string
  from_addr?: string
  to_addrs: string[]
  date?: string
  snippet?: string
}

export interface EmailThread {
  id: string
  project_id: string
  subject?: string
  participants: string[]
  last_message_date?: string
  fetched_at: string
  transaction_id?: string | null
  tag_source?: string | null
  messages?: EmailMessage[]
}
