import { defineConfig } from '@playwright/test';
export default defineConfig({testDir:'./e2e',timeout:90_000,expect:{timeout:30_000},workers:1,use:{baseURL:'http://127.0.0.1:5173',viewport:{width:1440,height:900},trace:'retain-on-failure'},reporter:'list'});
