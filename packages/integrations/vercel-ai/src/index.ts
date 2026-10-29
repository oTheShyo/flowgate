import type { CascadeAgent } from '@flowgate/core';
import { VercelAI } from '@flowgate/core';
import type { Tool } from '@flowgate/core';
import type { ToolExecutor } from '@flowgate/core';

export type VercelAIStreamProtocol = 'data' | 'text';

export interface VercelAIChatHandlerOptions {
  protocol?: VercelAIStreamProtocol;
  stream?: boolean;
  systemPrompt?: string;
  maxTokens?: number;
  temperature?: number;
  tools?: Tool[];
  extra?: Record<string, any>;
  toolExecutor?: ToolExecutor;
  toolHandlers?: Record<string, (args: Record<string, any>) => unknown | Promise<unknown>>;
  maxSteps?: number;
  forceDirect?: boolean;
  userTier?: string;
  emitCascadeEvents?: boolean;
  requestOverrides?: {
    enabled?: boolean;
    secret?: string;
    headerName?: string;
    allowedFields?: Array<'forceDirect' | 'maxSteps' | 'userTier'>;
  };
}

export const createChatHandler = (
  agent: CascadeAgent,
  options: VercelAIChatHandlerOptions = {}
) => VercelAI.createChatHandler(agent, options);

export const createCompletionHandler = (
  agent: CascadeAgent,
  options: VercelAIChatHandlerOptions = {}
) => VercelAI.createCompletionHandler(agent, options);

// Re-export the full namespace for advanced consumers (provider adapters, registries, etc.).
export { VercelAI };
