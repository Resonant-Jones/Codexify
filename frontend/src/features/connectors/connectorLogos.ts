import githubLogo from '@/assets/connectors/github.svg';

const CONNECTOR_LOGOS: Record<string, string> = {
  github: githubLogo,
};

export function getConnectorLogo(type?: string, id?: string): string | undefined {
  const key = (type || id || '').toLowerCase();
  return CONNECTOR_LOGOS[key];
}
