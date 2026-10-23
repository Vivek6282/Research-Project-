/**
 * Trackside Admin Dashboard — Shared Types and Interfaces.
 */

export interface UserRecord {
  id: string;
  username: string;
  driver_code?: string | null;
  name: string;
  role: "admin" | "coach" | "driver";
  status: string;
  email?: string;
  is_active?: boolean;
}

export interface DeviceRecord {
  id: string;
  device_type: string;
  status: string;
  assigned_to?: string | null;
  assigned_to_name?: string | null;
  is_online?: boolean;
  last_seen_at?: string | null;
  reassignment_notice?: string | null;
}

export interface AuditEntry {
  id: string;
  action: string;
  details?: string;
  actor_name?: string;
  target_user_name?: string;
  timestamp: string;
}

export interface DiagnosticsData {
  active_nodes: number;
  total_nodes: number;
  db_query_time_ms: number;
  user_count?: number;
  audit_count_30_days?: number;
  client_address_seen?: string;
  forwarded_for_entries?: number;
  trusted_proxy_count?: number;
}

export interface SuccessData {
  username: string;
  driver_code?: string | null;
  password: string;
  name: string;
  role: string;
}

export interface ConfirmModalState {
  isOpen: boolean;
  title: string;
  message: string;
  userToToggle: UserRecord | null;
  isCurrentlyActive: boolean;
}
