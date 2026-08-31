import { compileMDX } from 'next-mdx-remote/rsc'
import remarkGfm from 'remark-gfm'
import rehypeSlug from 'rehype-slug'
import rehypeAutolinkHeadings from 'rehype-autolink-headings'
import { Callout } from '@/components/mdx/Callout'
import { Card, CardGrid } from '@/components/mdx/Card'
import { Badge } from '@/components/mdx/Badge'
import { Steps, Step } from '@/components/mdx/Steps'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'
import { Tabs, TabItem } from '@/components/mdx/Tabs'
import { FileTree, FileTreeItem } from '@/components/mdx/FileTree'
import { Accordion, AccordionItem } from '@/components/mdx/Accordion'
import { Quote } from '@/components/mdx/Quote'
import { Kbd } from '@/components/mdx/Kbd'
import { Link } from '@/components/mdx/Link'

const mdxComponents = {
  Callout,
  Card,
  CardGrid,
  Badge,
  Steps,
  Step,
  MermaidDiagram,
  Tabs,
  TabItem,
  FileTree,
  FileTreeItem,
  Accordion,
  AccordionItem,
  Quote,
  Kbd,
  Link,
}

export async function compileMDXContent(source: string) {
  const { content } = await compileMDX({
    source,
    components: mdxComponents,
    options: {
      mdxOptions: {
        remarkPlugins: [remarkGfm],
        rehypePlugins: [rehypeSlug, [rehypeAutolinkHeadings, { behavior: 'wrap' }]],
      },
    },
  })
  return content
}
