---
description: Build frontend locally and commit if successful
auto_execution_mode: 2
---

1. Navigate to frontend directory: `cd frontend`
2. Run build command: `npm run build` or `ng build --configuration development`
3. Check build exit code:
   - If exit code is 0 (success): proceed to commit
   - If exit code is non-zero (failure): stop and report errors
4. If build successful:
   - Stage all changes: `git add -A`
   - Commit with descriptive message: `git commit -m "<description>"`
   - Push to develop: `git push origin develop`
5. If build failed:
   - Review error messages
   - Fix TypeScript/compilation errors
   - Retry build from step 2
// turbo
6. Verify build artifacts in `frontend/dist/` directory
