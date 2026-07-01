# Supabase RLS Implementation Guide

> **Type:** Stack implementation reference
> **Stack:** Supabase + PostgreSQL + pgvector
> **Project Origin:** an example multi-tenant backend architecture
> **Use When:** Building multi-tenant Supabase applications with RLS, storage, and vector search

---

## 1. Client Configuration (Next.js 16 App Router)

### Three Client Types

**Browser Client** (client components):
```typescript
// lib/supabase/client.ts
import { createBrowserClient } from '@supabase/ssr'
import { Database } from '@/types/supabase'

export function createClient() {
  return createBrowserClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

**Server Client** (server components, actions, route handlers):
```typescript
// lib/supabase/server.ts
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { Database } from '@/types/supabase'

export async function createClient() {
  const cookieStore = await cookies()
  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return cookieStore.getAll() },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options))
          } catch { /* Safe to ignore in Server Components */ }
        },
      },
    }
  )
}
```

**Admin Client** (service role, bypasses RLS):
```typescript
// lib/supabase/admin.ts
import { createClient } from '@supabase/supabase-js'
import { Database } from '@/types/supabase'

export const supabaseAdmin = createClient<Database>(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)
```

### Middleware (Session Refresh)

```typescript
// middleware.ts
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request })
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return request.cookies.getAll() },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options))
        },
      },
    }
  )
  const { data: { user } } = await supabase.auth.getUser()
  if (!user && request.nextUrl.pathname.startsWith('/dashboard')) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }
  return supabaseResponse
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
}
```

## 2. RLS Policy Templates

### Standard User Isolation
```sql
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

CREATE POLICY "{table}_select" ON {table_name} FOR SELECT TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "{table}_insert" ON {table_name} FOR INSERT TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "{table}_update" ON {table_name} FOR UPDATE TO authenticated
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "{table}_delete" ON {table_name} FOR DELETE TO authenticated
  USING (auth.uid() = user_id);
```

### Storage RLS (Folder-Based Isolation)
```sql
CREATE POLICY "Users access own files" ON storage.objects FOR SELECT TO authenticated
  USING (bucket_id = '{bucket}' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users upload own files" ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id = '{bucket}' AND auth.uid()::text = (storage.foldername(name))[1]);
-- Omit UPDATE/DELETE policies for immutable storage
```

## 3. Schema Template (Full Example)

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE plans (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE plan_documents (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  storage_path TEXT NOT NULL,
  file_name TEXT NOT NULL,
  file_size_bytes BIGINT NOT NULL,
  content_hash TEXT NOT NULL,
  mime_type TEXT NOT NULL DEFAULT 'application/pdf',
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(plan_id, content_hash)
);

CREATE TABLE extractions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  plan_document_id UUID NOT NULL REFERENCES plan_documents(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'review')),
  extracted_data JSONB,
  raw_ai_response JSONB,
  confidence_scores JSONB,
  flagged_fields JSONB DEFAULT '[]',
  prompt_version TEXT NOT NULL,
  model TEXT NOT NULL,
  reasoning_effort TEXT,
  duration_ms INTEGER,
  token_usage JSONB,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at BEFORE UPDATE ON plans
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

## 4. Connection Pooling

| Mode | Port | Use Case |
|------|------|----------|
| Transaction | 6543 | API Routes, serverless (DEFAULT) |
| Session | 5432 | Migrations, advisory locks |
| Direct | 5432 (db host) | One-time migrations only |

## 5. Performance Rules

1. Always use pooler URL (port 6543) in serverless
2. Add explicit `.eq('user_id', userId)` filters even with RLS (helps query planner)
3. Use `select('specific, columns')` not `select('*')`
4. GIN indexes on JSONB columns for containment queries
5. Batch inserts for embeddings: `.insert(rows)` not individual inserts
6. `EXPLAIN ANALYZE` for new query patterns

## 6. Environment Variables

```bash
NEXT_PUBLIC_SUPABASE_URL=https://[ref].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...         # Safe for client
SUPABASE_SERVICE_ROLE_KEY=eyJ...              # Server-only
```

## 7. Migration Workflow

```bash
supabase migration new {name}     # Generate migration
supabase db push                  # Apply locally
supabase db push --linked         # Apply to production
supabase gen types typescript --linked > types/supabase.ts
```

---

*Implementation guide from an example multi-tenant backend architecture*
