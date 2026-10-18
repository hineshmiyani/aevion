export function BackIcon() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m12 19-7-7 7-7M5 12h14" /></svg>;
}

export function SendIcon() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7" /></svg>;
}

export function ArrowIcon() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>;
}

export function LinkIcon() {
  return <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7" /><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7" /></svg>;
}

export function CheckIcon({ size = 15 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>;
}

// GitHub's mark, so a link says where it goes at a glance.
export function GitHubMark({ size = 12 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z" /></svg>;
}

function Stroke({ size = 16, children }: { size?: number; children: React.ReactNode }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{children}</svg>;
}

export const PlusIcon = () => <Stroke><path d="M12 5v14M5 12h14" /></Stroke>;
export const MinusIcon = () => <Stroke><path d="M5 12h14" /></Stroke>;
export const CloseIcon = () => <Stroke><path d="M18 6 6 18M6 6l12 12" /></Stroke>;
export const SearchIcon = () => <Stroke size={14}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></Stroke>;
export const ExternalIcon = () => <Stroke size={12}><path d="M7 17 17 7M8 7h9v9" /></Stroke>;
export const ExpandIcon = () => <Stroke><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" /></Stroke>;
export const CollapseIcon = () => <Stroke><path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7" /></Stroke>;
export const LayersIcon = () => <Stroke><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 13 9 5 9-5" /></Stroke>;
