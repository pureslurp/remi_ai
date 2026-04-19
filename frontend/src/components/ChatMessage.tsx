import ReactMarkdown from 'react-markdown'
import type { ChatMessage as Msg } from '../types'

interface Props {
  message: Msg
}

export default function ChatMessageBubble({ message }: Props) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold mr-2 mt-1 shrink-0">
          R
        </div>
      )}
      <div
        className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? 'max-w-[75%] bg-blue-600 text-white rounded-br-sm'
            : 'w-full bg-gray-800 text-gray-100 rounded-bl-sm'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
              ul: ({ children }) => (
                <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>
              ),
              li: ({ children }) => <li className="leading-relaxed">{children}</li>,
              strong: ({ children }) => (
                <strong className="font-semibold text-white">{children}</strong>
              ),
              em: ({ children }) => <em className="italic text-gray-300">{children}</em>,
              h1: ({ children }) => (
                <h1 className="text-base font-bold text-white mb-2 mt-3 first:mt-0">{children}</h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-sm font-bold text-white mb-2 mt-3 first:mt-0">{children}</h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-sm font-semibold text-white mb-1 mt-2 first:mt-0">{children}</h3>
              ),
              hr: () => <hr className="border-gray-600 my-3" />,
              blockquote: ({ children }) => (
                <blockquote className="border-l-2 border-gray-500 pl-3 my-2 text-gray-300 italic">
                  {children}
                </blockquote>
              ),
              code: ({ children, className }) => {
                const isBlock = className?.includes('language-')
                return isBlock ? (
                  <pre className="bg-gray-900 rounded-lg p-3 my-2 overflow-x-auto text-xs font-mono">
                    <code>{children}</code>
                  </pre>
                ) : (
                  <code className="bg-gray-900 px-1.5 py-0.5 rounded text-xs font-mono text-blue-300">
                    {children}
                  </code>
                )
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  )
}
