import { defineConfig, loadEnv } from 'vite';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig(({mode})=>{
  const env=loadEnv(mode,process.cwd(),'SAFARNAMA_');
  return {
    plugins: [tailwindcss()],
    server: {proxy: {'/api': env.SAFARNAMA_BACKEND_ORIGIN || 'http://localhost:8000'}},
  };
});
