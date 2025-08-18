import React from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

type Props = {
  children: React.ReactNode;
};

export const AppShell: React.FC<Props> = ({ children }) => {
  return (
    <div className="h-screen w-screen flex bg-bg text-fg">
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col">
        <Header />
        <main className="flex-1 min-w-0 overflow-auto p-4 bg-surface border-t border-muted/50">
          <div className="max-w-5xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
};
