import { Info, AlertTriangle, CheckCircle, Lightbulb, XCircle } from 'lucide-react'

type CalloutType = 'info' | 'warning' | 'success' | 'tip' | 'danger'

const CALLOUT_STYLES: Record<CalloutType, { bg: string; border: string; icon: React.ReactNode; label: string }> = {
  info: {
    bg: 'bg-db-info/5',
    border: 'border-db-info/30',
    icon: <Info className="w-5 h-5 text-db-info" />,
    label: 'Info',
  },
  warning: {
    bg: 'bg-db-warn/5',
    border: 'border-db-warn/30',
    icon: <AlertTriangle className="w-5 h-5 text-db-warn" />,
    label: 'Warning',
  },
  success: {
    bg: 'bg-db-accent/5',
    border: 'border-db-accent/30',
    icon: <CheckCircle className="w-5 h-5 text-db-accent" />,
    label: 'Success',
  },
  tip: {
    bg: 'bg-db-accent/5',
    border: 'border-db-accent/30',
    icon: <Lightbulb className="w-5 h-5 text-db-accent" />,
    label: 'Tip',
  },
  danger: {
    bg: 'bg-db-error/5',
    border: 'border-db-error/30',
    icon: <XCircle className="w-5 h-5 text-db-error" />,
    label: 'Danger',
  },
}

interface CalloutProps {
  type?: CalloutType
  title?: string
  children: React.ReactNode
}

export function Callout({ type = 'info', title, children }: CalloutProps) {
  const style = CALLOUT_STYLES[type]
  return (
    <div className={`rounded-lg border ${style.bg} ${style.border} p-4 my-6`}>
      <div className="flex items-center gap-2 mb-2">
        {style.icon}
        <span className="font-semibold text-sm text-db-text">{title || style.label}</span>
      </div>
      <div className="text-sm text-db-muted leading-7 pl-7">{children}</div>
    </div>
  )
}
