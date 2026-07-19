/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PERFECTBLUE_RUNTIME_URL?: string;
  readonly VITE_PERFECTBLUE_RUNTIME_TOKEN?: string;
  readonly VITE_CLAW3D_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
