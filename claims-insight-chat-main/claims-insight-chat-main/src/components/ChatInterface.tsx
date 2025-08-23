import React, { useState, useRef, useEffect } from 'react';
import { Send, Upload, Trash2, RotateCcw, Moon, Sun, Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ChatMessage } from './ChatMessage';
import { LoadingIndicator } from './LoadingIndicator';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  isStreaming?: boolean;
}

export const ChatInterface = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { toast } = useToast();

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Toggle dark mode
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  const generateId = () => Math.random().toString(36).substr(2, 9);

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: generateId(),
      content: inputValue.trim(),
      role: 'user',
      timestamp: new Date(),
    };

    const assistantMessageId = generateId();
    const assistantMessage: Message = {
      id: assistantMessageId,
      content: '',
      role: 'assistant',
      timestamp: new Date(),
      isStreaming: true,
    };

    setMessages(prev => [...prev, userMessage, assistantMessage]);
    setInputValue('');
    setIsLoading(true);
    setStreamingMessageId(assistantMessageId);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: userMessage.content }),
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const reader = response.body?.getReader();
const decoder = new TextDecoder();

if (reader) {
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    console.log('Raw chunk received:', chunk); // Debug log
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.trim()) { // Changed from line.startsWith('data: ')
        try {
          const data = JSON.parse(line); // Changed from line.slice(6)
          
          if (data.type === 'final_summary_chunk') {
            setMessages(prev => prev.map(msg => 
              msg.id === assistantMessageId 
                ? { ...msg, content: msg.content + data.content }
                : msg
            ));
          } else if (data.type === 'done') {
            setMessages(prev => prev.map(msg => 
              msg.id === assistantMessageId 
                ? { ...msg, isStreaming: false }
                : msg
            ));
            break;
          } else if (data.type === 'error') {
            toast({
              title: "Error",
              description: data.message || "An error occurred",
              variant: "destructive",
            });
            break;
          }
        } catch (e) {
          console.log('JSON parse error:', e, 'Line:', line); // Debug log
        }
      }
    }
  }
}
    } catch (error) {
      toast({
        title: "Connection Error",
        description: "Failed to connect to the chat service",
        variant: "destructive",
      });
      
      setMessages(prev => prev.filter(msg => msg.id !== assistantMessageId));
    } finally {
      setIsLoading(false);
      setStreamingMessageId(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const formData = new FormData();
    Array.from(files).forEach(file => {
      formData.append('files', file);
    });

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        toast({
          title: "Success",
          description: `${files.length} file(s) uploaded successfully`,
        });
      } else {
        throw new Error('Upload failed');
      }
    } catch (error) {
      toast({
        title: "Upload Error",
        description: "Failed to upload files",
        variant: "destructive",
      });
    }

    // Reset input
    event.target.value = '';
  };

  const clearData = async () => {
    try {
      const response = await fetch('/api/data/clear', {
        method: 'POST',
      });

      if (response.ok) {
        toast({
          title: "Success",
          description: "Claims data cleared successfully",
        });
      } else {
        throw new Error('Clear failed');
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to clear data",
        variant: "destructive",
      });
    }
  };

  const resetChat = () => {
    setMessages([]);
    toast({
      title: "Chat Reset",
      description: "Chat history has been cleared",
    });
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar - Hidden on mobile */}
      <div className="hidden md:flex w-64 bg-card border-r border-border p-4 flex-col">
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-foreground mb-4">Actions</h2>
          
          <div className="space-y-3">
            <label className="block">
              <input
                type="file"
                multiple
                accept=".csv"
                onChange={handleUpload}
                className="hidden"
              />
              <Button variant="outline" className="w-full justify-start" asChild>
                <span className="cursor-pointer">
                  <Upload className="mr-2 h-4 w-4" />
                  Upload CSV
                </span>
              </Button>
            </label>

            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={clearData}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Clear Data
            </Button>

            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={resetChat}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              Reset Chat
            </Button>
          </div>
        </div>

        <div className="mt-auto">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="w-full"
          >
            {isDarkMode ? <Sun className="mr-2 h-4 w-4" /> : <Moon className="mr-2 h-4 w-4" />}
            {isDarkMode ? 'Light Mode' : 'Dark Mode'}
          </Button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-card border-b border-border p-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-foreground">Claims AI Assistant</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Analyze your claims data and get insights
              </p>
            </div>
            
            {/* Mobile Menu */}
            <div className="md:hidden flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsDarkMode(!isDarkMode)}
              >
                {isDarkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
              
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Menu className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem asChild>
                    <label className="flex items-center cursor-pointer">
                      <input
                        type="file"
                        multiple
                        accept=".csv"
                        onChange={handleUpload}
                        className="hidden"
                      />
                      <Upload className="mr-2 h-4 w-4" />
                      Upload CSV
                    </label>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={clearData}>
                    <Trash2 className="mr-2 h-4 w-4" />
                    Clear Data
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={resetChat}>
                    <RotateCcw className="mr-2 h-4 w-4" />
                    Reset Chat
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <h3 className="text-lg font-medium text-foreground mb-2">
                  Welcome to Claims AI Assistant
                </h3>
                <p className="text-muted-foreground">
                  Upload your CSV files and start asking questions about your claims data
                </p>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                isStreaming={message.isStreaming}
              />
            ))
          )}
          
          {isLoading && <LoadingIndicator />}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-card border-t border-border">
          <div className="flex items-end space-x-2">
            <div className="flex-1">
              <Textarea
                ref={textareaRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your claims data..."
                className="resize-none min-h-[60px] max-h-32"
                disabled={isLoading}
              />
            </div>
            <Button
              onClick={sendMessage}
              disabled={!inputValue.trim() || isLoading}
              size="sm"
              className="px-4 py-2"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
};