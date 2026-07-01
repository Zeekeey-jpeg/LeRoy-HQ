---
name: supabase-netlify
description: |
  Stack A: Modern SaaS deployment with Supabase + Netlify.

  Use when building:
  - New SaaS products
  - Public-facing applications
  - Projects requiring relational database
  - Modern auth (OAuth, email/password)
  - Scalable production deployments

  Includes: PostgreSQL, Auth, Storage, Realtime, Edge Functions.
---

# Stack A: Supabase + Netlify

## When to Use
- New SaaS products
- Public-facing applications
- Projects requiring relational database
- Modern auth (OAuth, email/password)
- Scalable production deployments

## Architecture

```
              NETLIFY + SUPABASE
  Frontend    | app.netlify.com (from GitHub)
  Auth        | Supabase Auth (email, OAuth)
  Database    | Supabase PostgreSQL
  Storage     | Supabase Storage
  Realtime    | Supabase Subscriptions
  Functions   | Supabase Edge / Netlify Funcs
  Repo        | github.com/<your-github>
```

## Key Patterns

### Authentication
```typescript
// Initialize Supabase client
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_ANON_KEY!
)

// Sign up
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password123'
})

// Sign in
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password123'
})

// Get current user
const { data: { user } } = await supabase.auth.getUser()
```

### Row Level Security (RLS)
```sql
-- Enable RLS
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own data
CREATE POLICY "Users see own data" ON products
  FOR SELECT
  USING (auth.uid() = user_id);

-- Policy: Users can insert their own data
CREATE POLICY "Users insert own data" ON products
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);
```

### Database Queries
```typescript
// Select with filters
const { data, error } = await supabase
  .from('products')
  .select('*')
  .eq('status', 'active')
  .order('created_at', { ascending: false })
  .limit(10)

// Insert
const { data, error } = await supabase
  .from('products')
  .insert({ name: 'Widget', price: 99.99 })
  .select()

// Update
const { data, error } = await supabase
  .from('products')
  .update({ price: 109.99 })
  .eq('id', productId)
  .select()

// Upsert
const { data, error } = await supabase
  .from('products')
  .upsert({ id: productId, name: 'Widget', price: 109.99 })
  .select()
```

### Realtime Subscriptions
```typescript
const channel = supabase
  .channel('products')
  .on(
    'postgres_changes',
    { event: '*', schema: 'public', table: 'products' },
    (payload) => {
      console.log('Change received!', payload)
    }
  )
  .subscribe()
```

### Storage
```typescript
// Upload file
const { data, error } = await supabase.storage
  .from('avatars')
  .upload('public/avatar.png', file)

// Get public URL
const { data } = supabase.storage
  .from('avatars')
  .getPublicUrl('public/avatar.png')
```

## Netlify Configuration

### netlify.toml
```toml
[build]
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "18"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-Content-Type-Options = "nosniff"
```

### Environment Variables

> **CREDENTIALS:** See `skills/memory/config/credentials.md` > Supabase section for environment variable patterns and project-specific setup.

```
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
```

## CI/CD Flow

```
1. Push to GitHub main branch
2. Netlify detects change
3. Runs build command
4. Deploys to CDN
5. Preview URL for PRs
```

## Example Projects
- your org SaaS tools
- your organization Solutions catalog
- New client portals
- Subscription products
