"use client";

import { Box, Typography } from "@mui/material";

import AdminChatConsole from "@/components/AdminChatConsole";

export default function AdminChatbotPage() {
  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography fontSize={28} fontWeight={800} color="#111827">
          Chatbot Tester
        </Typography>
        <Typography fontSize={14} color="text.secondary" sx={{ mt: 0.75 }}>
          Run test conversations as an admin, review the assistant response, and keep a saved history of your test sessions.
        </Typography>
      </Box>

      <AdminChatConsole />
    </Box>
  );
}
