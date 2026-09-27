export type ChatAnswerBlock =
  | { kind: "heading"; text: string }
  | { kind: "text"; text: string };

const MARKDOWN_HEADING = /^(?:\\+)?#{1,6}[ \t]+(\S(?:.*\S)?)\s*$/;
const PLAIN_SECTION = /^(?:why it matched|what['’]s missing)$/i;

function headingFromLine(line: string): string | null {
  const trimmed = line.trim();
  const markdown = MARKDOWN_HEADING.exec(trimmed);
  if (markdown) return markdown[1];
  if (PLAIN_SECTION.test(trimmed)) return trimmed;
  return null;
}

/** Split an assistant answer into headings and the paragraphs between them. */
export function splitChatAnswer(content: string): ChatAnswerBlock[] {
  const blocks: ChatAnswerBlock[] = [];
  const buffer: string[] = [];

  const flush = () => {
    const text = buffer.join("\n").replace(/^\n+|\n+$/g, "");
    buffer.length = 0;
    if (text.trim().length === 0) return;
    blocks.push({ kind: "text", text });
  };

  for (const line of content.split(/\r\n|\n/)) {
    const heading = headingFromLine(line);
    if (heading !== null) {
      flush();
      blocks.push({ kind: "heading", text: heading });
    } else {
      buffer.push(line);
    }
  }
  flush();
  return blocks;
}
