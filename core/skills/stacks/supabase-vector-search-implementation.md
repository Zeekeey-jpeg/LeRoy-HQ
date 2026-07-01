# Supabase pgvector Implementation Guide

> **Type:** Stack implementation reference
> **Stack:** Supabase + pgvector + OpenAI Embeddings
> **Project Origin:** an example multi-tenant backend architecture
> **Use When:** Building RAG pipelines with pgvector on Supabase

---

## 1. Setup

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 2. Embedding Table Design

```sql
CREATE TABLE training_embeddings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  extraction_id UUID NOT NULL,
  content TEXT NOT NULL,
  content_type TEXT NOT NULL CHECK (content_type IN ('correction', 'example', 'plan_section')),
  embedding vector(1536) NOT NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE training_embeddings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users view own" ON training_embeddings FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert own" ON training_embeddings FOR INSERT WITH CHECK (auth.uid() = user_id);
```

## 3. Index Selection

### HNSW (Preferred)
```sql
CREATE INDEX ON training_embeddings
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```
- Faster queries, higher memory
- Best for production with moderate dataset sizes

### IVFFlat (Alternative)
```sql
CREATE INDEX ON training_embeddings
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);  -- sqrt(row_count) as rule of thumb
```
- Lower memory, requires training on existing data

## 4. Distance Operators

| Operator | Type | When to Use |
|----------|------|-------------|
| `<=>` | Cosine | **Default for OpenAI** (normalized vectors) |
| `<->` | Euclidean (L2) | When magnitude matters |
| `<#>` | Inner product | Non-normalized embeddings |

## 5. Similarity Search RPC

```sql
CREATE OR REPLACE FUNCTION match_training_embeddings(
  query_embedding vector(1536),
  match_count int DEFAULT 5,
  match_threshold float DEFAULT 0.7,
  filter_mechanic_type text DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  training_example_id UUID,
  content TEXT,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    te.id,
    te.extraction_id AS training_example_id,
    te.content,
    1 - (te.embedding <=> query_embedding) AS similarity
  FROM training_embeddings te
  WHERE
    te.user_id = auth.uid()
    AND (filter_mechanic_type IS NULL OR te.metadata->>'mechanic_type' = filter_mechanic_type)
    AND 1 - (te.embedding <=> query_embedding) > match_threshold
  ORDER BY te.embedding <=> query_embedding
  LIMIT match_count;
$$;
```

## 6. TypeScript Embedding Service

```typescript
import OpenAI from 'openai'
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY! })

export class EmbeddingService {
  async generateEmbeddings(texts: string[]): Promise<number[][]> {
    const response = await openai.embeddings.create({
      model: 'text-embedding-3-small',  // 1536 dims, $0.02/1M tokens
      input: texts,
      encoding_format: 'float',
    })
    return response.data
      .sort((a, b) => a.index - b.index)
      .map(item => item.embedding)
  }

  async generateQueryEmbedding(text: string): Promise<number[]> {
    const [embedding] = await this.generateEmbeddings([text])
    return embedding
  }
}
```

## 7. RAG Retrieval Service

```typescript
export class RagService {
  constructor(private supabase: SupabaseClient, private embeddingService: EmbeddingService) {}

  async retrieveRelevantExamples(planText: string, options = {}) {
    const { maxResults = 5, mechanicType, minSimilarity = 0.7 } = options
    const queryText = planText.substring(0, 8000)
    const queryEmbedding = await this.embeddingService.generateQueryEmbedding(queryText)

    const { data: results, error } = await this.supabase.rpc(
      'match_training_embeddings',
      {
        query_embedding: queryEmbedding,
        match_count: maxResults,
        match_threshold: minSimilarity,
        filter_mechanic_type: mechanicType || null,
      }
    )

    if (error) { console.error('RAG retrieval error:', error); return [] }
    if (!results?.length) return []

    const { data: examples } = await this.supabase
      .from('training_examples')
      .select('input_text, output_data')
      .in('id', results.map(r => r.training_example_id))

    return (examples || []).map((ex, i) => ({
      input: ex.input_text,
      output: ex.output_data,
      similarity: results[i]?.similarity || 0,
    }))
  }
}
```

## 8. Embedding Model Comparison

| Model | Dimensions | Cost/1M tokens | Recommendation |
|-------|-----------|----------------|----------------|
| text-embedding-3-small | 1536 | $0.02 | **Default choice** |
| text-embedding-3-large | 3072 | $0.13 | Higher accuracy when needed |
| text-embedding-ada-002 | 1536 | $0.10 | Legacy -- do not use |

## 9. Training Example Creation from Corrections

```typescript
async createFromCorrection(review, planText) {
  const textToEmbed = `${planText}\n\nCorrection: ${review.field_path} should be ${
    JSON.stringify(review.corrected_value)} because ${review.correction_reason}`

  const [embedding] = await this.embeddingService.generateEmbeddings([textToEmbed])

  await this.supabase.from('training_embeddings').insert({
    user_id: userId,
    extraction_id: review.extraction_id,
    content: textToEmbed,
    content_type: 'correction',
    embedding: embedding,
    metadata: { mechanic_type, field_path: review.field_path },
  })
}
```

## 10. Chunking Strategy

Chunk by logical section, NOT token count:
- Each compensation plan measure = one chunk (even if 2-3 pages)
- Rate tables must NEVER be split across chunks
- Include section headers in each chunk for context
- Overlap ~100 chars between chunks for continuity

---

*Implementation guide from an example multi-tenant backend architecture*
