declare module 'parlant-chat-react' {
  import { ReactNode } from 'react';

  export interface ParlantChatboxProps {
    server: string;
    agentId: string;
    sessionId?: string;
    customerId?: string;
    titleFn?: () => string;
    float?: boolean;
    popupButton?: ReactNode;
    initialMessage?: {
      kind: string;
      source: string;
      message: string;
    };
    classNames?: {
      chatboxWrapper?: string;
      chatbox?: string;
      messagesArea?: string;
      agentMessage?: string;
      customerMessage?: string;
      textarea?: string;
      popupButton?: string;
      popupButtonIcon?: string;
      chatDescription?: string;
      bottomLine?: string;
    };
    components?: {
      popupButton?: (props: { toggleChatOpen: () => void }) => ReactNode;
      agentMessage?: (props: { message: any }) => ReactNode;
      customerMessage?: (props: { message: any }) => ReactNode;
      header?: (props: { changeIsExpanded: () => void }) => ReactNode;
    };
  }

  const ParlantChatbox: React.FC<ParlantChatboxProps>;
  export default ParlantChatbox;
}


