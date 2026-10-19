/**
 * Trackside Admin Dashboard — Shared Types and Interfaces.
 */

export interface UserRecord {
  id: string;
  username: string;
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
  packet_drops_last_60_min: number;
  is_simulated_packet_data: boolean;
}

export interface SuccessData {
  username: string;
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
