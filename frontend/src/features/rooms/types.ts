export type HostedRoomParticipant = {
  id: string;
  display_name: string;
  kind: string;
  role: string;
  state: string;
  joined_at: string;
  removed_at?: string | null;
  actor_source?: string | null;
  actor_ref?: string | null;
};

export type HostedRoomInvitation = {
  id: string;
  intended_display_name: string;
  status: string;
  expires_at?: string | null;
  accepted_at?: string | null;
  revoked_at?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type HostedRoomDetail = {
  id: string;
  slug: string;
  title: string;
  status: string;
  backing_thread_id: number;
  enabled_actors: Array<Record<string, string>>;
  active_participant_count: number;
  pending_invitation_count: number;
  created_at: string;
  updated_at: string;
  closed_at?: string | null;
  participants: HostedRoomParticipant[];
  invitations: HostedRoomInvitation[];
};

export type HostedRoomMessageSender = {
  participant_id: string;
  display_name: string | null;
};

export type HostedRoomMessage = {
  id: number;
  role: string;
  content: string;
  created_at: string;
  sender: HostedRoomMessageSender | null;
};
