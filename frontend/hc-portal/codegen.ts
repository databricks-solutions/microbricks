import type { CodegenConfig } from "@graphql-codegen/cli";

const config: CodegenConfig = {
  schema: "http://localhost:8000/api/graphql",
  documents: ["src/hc_portal/ui/graphql/**/*.graphql"],
  generates: {
    "src/hc_portal/ui/lib/graphql/generated/": {
      preset: "client",
      config: {
        documentMode: "string",
      },
    },
  },
};

export default config;
