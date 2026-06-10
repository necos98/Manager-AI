## Plan

Single file change in `frontend/src/routes/queue.tsx`.

### Step 1: Move `useSetAutoProcess()` before the early return

Current code (line 70):
```tsx
const setAutoProcess = useSetAutoProcess();
```

This is called AFTER the loading early return block. Move it to the top of the component, grouping with the other hooks (after line 33, before the useEffect).

### Step 2: Verify syntax

Run `python -c "import ast; ast.parse(open('frontend/src/routes/queue.tsx').read())"` to verify the file parses correctly.

### Step 3: Verify frontend build

Run `npm run lint` in the frontend directory to catch any TypeScript issues.
