import { defineConfig, loadEnv } from 'vite';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig(({mode})=>{
  const env=loadEnv(mode,process.cwd(),'SAFARNAMA_');
  const backend = env.SAFARNAMA_BACKEND_ORIGIN || 'http://localhost:8000';
  const proxy = {'/api': backend, '/health': backend, '/ready': backend};
  return {
    plugins: [tailwindcss()],
    server: {proxy},
    preview: {proxy},
  };
});
