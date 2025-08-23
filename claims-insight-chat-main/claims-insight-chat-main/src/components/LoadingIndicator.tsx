import React from 'react';
import { Bot } from 'lucide-react';
import { cn } from '@/lib/utils';

export const LoadingIndicator: React.FC = () => {
  return (
    <div className="flex justify-start">
      <div className="flex max-w-[70%] space-x-3">
        {/* Avatar */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-secondary text-secondary-foreground">
          <Bot className="w-4 h-4" />
        </div>

        {/* Loading Bubble */}
        <div className="bg-secondary text-secondary-foreground rounded-2xl px-4 py-3 shadow-sm">
          <div className="flex items-center space-x-1">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-current rounded-full animate-bounce [animation-delay:-0.3s]"></div>
              <div className="w-2 h-2 bg-current rounded-full animate-bounce [animation-delay:-0.15s]"></div>
              <div className="w-2 h-2 bg-current rounded-full animate-bounce"></div>
            </div>
            <span className="text-sm ml-2 opacity-70">Thinking...</span>
          </div>
        </div>
      </div>
    </div>
  );
};