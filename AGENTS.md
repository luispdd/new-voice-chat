<!-- Project execution notes-->
<!-- General guidance about how to build the proejct. -->

# General Guidelines for generating the code

- The different building blocks must be created using the generators of each library (Ex: `nx run shared-components:generate`, `nx run api-sdk:generate`).
- Install the required CLI component of the libraries before using them. For example, make sure the required generator package are installed.
- For node.js package managers, use `bun` and `bunx instead of `npm` and `npx`.
- For python package managers, use `uv` instead of `pip`.

## Instructions about the project blocks

- Refer to `project-architecture-and-tooling-analysis.md` for information about the different blocks of the project. Use this file to understand the project structure and the tooling strategy to follow.

<!-- Project execution notes end--> 
