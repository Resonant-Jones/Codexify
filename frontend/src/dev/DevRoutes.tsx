// src/dev/DevRoutes.tsx
import React from 'react';

export default function DevRoutes() {
  const UITunePad = React.lazy(() => import('./ui-tune/UITunePad'));
  return (
    <React.Suspense fallback={null}>
      <UITunePad />
    </React.Suspense>
  );
}
