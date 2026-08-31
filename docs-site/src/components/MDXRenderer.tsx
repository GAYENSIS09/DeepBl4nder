import { compileMDXContent } from '@/lib/mdx'

interface MDXRendererProps {
  source: string
}

export async function MDXRenderer({ source }: MDXRendererProps) {
  const content = await compileMDXContent(source)
  return <>{content}</>
}
