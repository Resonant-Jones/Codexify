import { FormEvent, useEffect, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import SettingsSectionCard from "@/features/settings/components/SettingsSectionCard";
import { useAuthState } from "@/lib/authState";
import {
  getUserProfile,
  updateUserProfile,
  type UserProfileRecord,
} from "@/features/userProfile/api";

type UserProfileFormState = {
  displayName: string;
  avatarUrl: string;
  timezone: string;
};

const EMPTY_FORM_STATE: UserProfileFormState = {
  displayName: "",
  avatarUrl: "",
  timezone: "",
};

const LOADING_AUTH_MESSAGE = "Checking authentication...";
const AUTH_REQUIRED_TITLE = "Authentication required";
const AUTH_REQUIRED_MESSAGE =
  "Sign in to manage the profile metadata tied to this session.";
const LOAD_ERROR_MESSAGE = "Unable to load user profile. Please try again.";
const SAVE_ERROR_MESSAGE = "Unable to save profile changes. Please try again.";
const SAVE_SUCCESS_MESSAGE = "Profile saved.";
const LOADING_PROFILE_MESSAGE = "Loading current profile...";

function normalizeField(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function toFormState(profile: UserProfileRecord | null): UserProfileFormState {
  return {
    displayName: profile?.display_name ?? "",
    avatarUrl: profile?.avatar_url ?? "",
    timezone: profile?.timezone ?? "",
  };
}

function isFormDirty(
  profile: UserProfileRecord | null,
  formState: UserProfileFormState
): boolean {
  if (!profile) return false;

  return (
    normalizeField(formState.displayName) !== profile.display_name ||
    normalizeField(formState.avatarUrl) !== profile.avatar_url ||
    normalizeField(formState.timezone) !== profile.timezone
  );
}

function ProfileMessageCard({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: ReactNode;
}) {
  return (
    <SettingsSectionCard className="space-y-3">
      <div className="space-y-2">
        <h2 className="text-base font-semibold tracking-[-0.02em]">{title}</h2>
        <p className="text-sm leading-6 text-[var(--muted)]">{message}</p>
      </div>
      {action ? <div>{action}</div> : null}
    </SettingsSectionCard>
  );
}

export default function UserProfilePage() {
  const auth = useAuthState();
  const [profile, setProfile] = useState<UserProfileRecord | null>(null);
  const [formState, setFormState] = useState<UserProfileFormState>(
    EMPTY_FORM_STATE
  );
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [loadNonce, setLoadNonce] = useState(0);

  useEffect(() => {
    if (!auth.ready) {
      setLoadingProfile(true);
      return;
    }

    if (auth.status !== "authenticated") {
      setProfile(null);
      setFormState(EMPTY_FORM_STATE);
      setLoadingProfile(false);
      setLoadError(null);
      setSaveError(null);
      setSaveStatus(null);
      return;
    }

    let cancelled = false;
    setLoadingProfile(true);
    setLoadError(null);
    setSaveError(null);
    setSaveStatus(null);

    void (async () => {
      try {
        const nextProfile = await getUserProfile();
        if (cancelled) return;
        setProfile(nextProfile);
        setFormState(toFormState(nextProfile));
      } catch {
        if (cancelled) return;
        setProfile(null);
        setFormState(EMPTY_FORM_STATE);
        setLoadError(LOAD_ERROR_MESSAGE);
      } finally {
        if (!cancelled) {
          setLoadingProfile(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [auth.ready, auth.status, auth.token, loadNonce]);

  const authChecking = !auth.ready;
  const authBlocked = auth.ready && auth.status !== "authenticated";
  const dirty = isFormDirty(profile, formState);
  const canSave = Boolean(profile) && !loadingProfile && !saving && dirty;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSave) return;

    setSaving(true);
    setSaveError(null);
    setSaveStatus(null);

    try {
      const nextProfile = await updateUserProfile({
        display_name: normalizeField(formState.displayName),
        avatar_url: normalizeField(formState.avatarUrl),
        timezone: normalizeField(formState.timezone),
      });
      setProfile(nextProfile);
      setFormState(toFormState(nextProfile));
      setSaveStatus(SAVE_SUCCESS_MESSAGE);
    } catch {
      setSaveError(SAVE_ERROR_MESSAGE);
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-screen bg-[var(--color-surface)] px-6 py-10 text-[var(--text)]">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--muted)]">
            Account
          </p>
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold tracking-[-0.03em]">
              User Profile
            </h1>
            <p className="max-w-2xl text-sm leading-6 text-[var(--muted)]">
              Update the presentation metadata for this authenticated session.
              These values are account metadata only and stay separate from
              persona behavior.
            </p>
          </div>
        </header>

        {authChecking ? (
          <ProfileMessageCard
            title={LOADING_AUTH_MESSAGE}
            message="The browser session is still being resolved before profile metadata can load."
          />
        ) : authBlocked ? (
          <ProfileMessageCard
            title={AUTH_REQUIRED_TITLE}
            message={AUTH_REQUIRED_MESSAGE}
            action={
              <a className="text-sm underline underline-offset-2" href="/login">
                Go to sign in
              </a>
            }
          />
        ) : loadingProfile ? (
          <ProfileMessageCard
            title={LOADING_PROFILE_MESSAGE}
            message="Fetching your current account metadata."
          />
        ) : loadError ? (
          <SettingsSectionCard className="space-y-3">
            <div
              role="alert"
              className="rounded-[var(--tile-radius)] border px-4 py-3 text-sm"
              style={{
                borderColor: "var(--panel-border)",
                background:
                  "color-mix(in srgb, var(--panel-bg) 92%, transparent)",
              }}
            >
              {loadError}
            </div>
            <div className="flex flex-wrap gap-3">
              <Button type="button" onClick={() => setLoadNonce((value) => value + 1)}>
                Retry
              </Button>
            </div>
          </SettingsSectionCard>
        ) : (
          <SettingsSectionCard className="space-y-5">
            <div className="space-y-2">
              <h2 className="text-base font-semibold tracking-[-0.02em]">
                Profile metadata
              </h2>
              <p className="text-sm leading-6 text-[var(--muted)]">
                These fields are editable presentation metadata. They do not
                expose canonical ownership fields or persona settings.
              </p>
            </div>

            {saveError ? (
              <div
                role="alert"
                className="rounded-[var(--tile-radius)] border px-4 py-3 text-sm"
                style={{
                  borderColor: "var(--panel-border)",
                  background:
                    "color-mix(in srgb, var(--panel-bg) 92%, transparent)",
                }}
              >
                {saveError}
              </div>
            ) : null}

            {saveStatus ? (
              <div
                role="status"
                aria-live="polite"
                className="rounded-[var(--tile-radius)] border px-4 py-3 text-sm"
                style={{
                  borderColor: "var(--panel-border)",
                  background:
                    "color-mix(in srgb, var(--panel-bg) 92%, transparent)",
                }}
              >
                {saveStatus}
              </div>
            ) : null}

            <form className="space-y-4" onSubmit={handleSubmit}>
              <label className="block space-y-2" htmlFor="display-name">
                <span className="text-sm font-medium">Display name</span>
                <Input
                  id="display-name"
                  value={formState.displayName}
                  onChange={(event) => {
                    setSaveError(null);
                    setSaveStatus(null);
                    setFormState((current) => ({
                      ...current,
                      displayName: event.target.value,
                    }));
                  }}
                  placeholder="How should this account be shown?"
                  autoComplete="name"
                />
              </label>

              <label className="block space-y-2" htmlFor="avatar-url">
                <span className="text-sm font-medium">Avatar URL</span>
                <Input
                  id="avatar-url"
                  type="url"
                  value={formState.avatarUrl}
                  onChange={(event) => {
                    setSaveError(null);
                    setSaveStatus(null);
                    setFormState((current) => ({
                      ...current,
                      avatarUrl: event.target.value,
                    }));
                  }}
                  placeholder="https://example.com/avatar.png"
                  autoComplete="url"
                />
              </label>

              <label className="block space-y-2" htmlFor="timezone">
                <span className="text-sm font-medium">Timezone</span>
                <Input
                  id="timezone"
                  value={formState.timezone}
                  onChange={(event) => {
                    setSaveError(null);
                    setSaveStatus(null);
                    setFormState((current) => ({
                      ...current,
                      timezone: event.target.value,
                    }));
                  }}
                  placeholder="America/New_York"
                  autoComplete="off"
                />
              </label>

              <div className="flex flex-wrap items-center gap-3">
                <Button type="submit" disabled={!canSave}>
                  {saving ? "Saving..." : "Save profile"}
                </Button>
                <span className="text-sm text-[var(--muted)]">
                  {dirty
                    ? "You have unsaved metadata changes."
                    : "No metadata changes pending."}
                </span>
              </div>
            </form>
          </SettingsSectionCard>
        )}
      </div>
    </main>
  );
}
