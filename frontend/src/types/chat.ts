export type ChatExecution = {
  attempted_provider: string;
  attempted_model: string;
  final_provider: string;
  final_model: string;
  fallback_triggered: boolean;
};
