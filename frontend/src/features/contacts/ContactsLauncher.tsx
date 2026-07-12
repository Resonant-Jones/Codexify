import { ContactRound } from "lucide-react";
import { useState } from "react";

import ContactsWindow from "./ContactsWindow";

type ContactsLauncherProps = {
  className?: string;
};

export default function ContactsLauncher({ className }: ContactsLauncherProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        className={className}
        data-testid="contacts-launcher"
        aria-label="Contacts"
        title="Contacts"
        onClick={() => setOpen(true)}
      >
        <ContactRound className="h-4 w-4" aria-hidden="true" />
      </button>
      <ContactsWindow open={open} onClose={() => setOpen(false)} contacts={[]} />
    </>
  );
}
