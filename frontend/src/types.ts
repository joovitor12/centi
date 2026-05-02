export interface User {
  user_email: string;
  listen_address: string;
  has_calendar_access: boolean;
  parlant_session_id?: string;
}

export interface Session {
  session_id: string;
  user_email: string;
  exists: boolean;
}

export interface AuthStatus {
  authenticated: boolean;
  user_email?: string;
  has_calendar_access?: boolean;
}

