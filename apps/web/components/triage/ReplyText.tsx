import { Fragment, type ReactNode } from "react";

// The drafted reply is Markdown with `code`, **bold** and [text](https://…) links. Like
// AnswerText, this renders React nodes only: no HTML from the model ever reaches the page.
const TOKEN = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\(https:\/\/[^)\s]+\))/g;

export function inline(text: string): ReactNode[] {
  return text.split(TOKEN).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={i} className="rounded-sm bg-paper px-1 py-0.5 font-mono text-[0.8em]">{part.slice(1, -1)}</code>;
    }
    const link = /^\[([^\]]+)\]\((https:\/\/[^)\s]+)\)$/.exec(part);
    if (link) {
      return (
        <a key={i} href={link[2]} target="_blank" rel="noreferrer" className="underline decoration-rule-strong underline-offset-2 hover:decoration-path">
          {inline(link[1])}
        </a>
      );
    }
    return <Fragment key={i}>{part}</Fragment>;
  });
}

export function ReplyText({ text }: { text: string }) {
  return (
    <div className="space-y-3 font-serif text-[17px] leading-[1.65] text-ink">
      {text.split(/\n{2,}/).map((block, i) => (
        <p key={i}>{inline(block.replace(/\n/g, " "))}</p>
      ))}
    </div>
  );
}

/** One line of GitHub-style text, such as an issue title: `code` renders as code. */
export function InlineText({ text }: { text: string }) {
  return <>{inline(text)}</>;
}

