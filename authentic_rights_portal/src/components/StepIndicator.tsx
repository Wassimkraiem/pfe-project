"use client";

import { Check } from "lucide-react";
import { Box, Typography } from "@mui/material";

interface Step {
  number: number;
  label: string;
}

interface StepIndicatorProps {
  steps: Step[];
  currentStep: number;
}

export default function StepIndicator({
  steps,
  currentStep,
}: StepIndicatorProps) {
  const stepCount = steps.length || 1;
  const stepWidth = 100 / stepCount;
  const lineInset = `${stepWidth / 2}%`;
  const activeLineWidth =
    stepCount > 1 ? `${((currentStep - 1) / (stepCount - 1)) * (100 - stepWidth)}%` : "0%";

  return (
    <Box sx={{ width: "100%", px: { xs: 1, sm: 2 } }}>
      {/* Steps with connecting lines */}
      <Box
        sx={{
          position: "relative",
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
        }}
      >
        {/* Background line - spans between first and last step circles */}
        <Box
          sx={{
            position: "absolute",
            top: { xs: 12, sm: 16 },
            left: lineInset,
            right: lineInset,
            height: 2,
            bgcolor: "#e5e7eb",
            zIndex: 0,
          }}
        />

        {/* Active line overlay */}
        <Box
          sx={{
            position: "absolute",
            top: { xs: 12, sm: 16 },
            left: lineInset,
            height: 2,
            bgcolor: "#4D8AFF",
            transition: "all 0.3s",
            zIndex: 0,
            width: currentStep > 1 ? activeLineWidth : "0%",
          }}
        />

        {steps.map((step) => (
          <Box
            key={step.number}
            sx={{
              position: "relative",
              zIndex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              width: `${stepWidth}%`,
            }}
          >
            {/* Step Circle */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: { xs: 24, sm: 32 },
                height: { xs: 24, sm: 32 },
                borderRadius: "50%",
                border: "2px solid",
                fontSize: { xs: "0.75rem", sm: "0.875rem" },
                fontWeight: 500,
                transition: "all 0.2s",
                borderColor: currentStep >= step.number ? "#4D8AFF" : "#d1d5db",
                bgcolor: currentStep >= step.number ? "#4D8AFF" : "white",
                color: currentStep >= step.number ? "white" : "#9ca3af",
              }}
            >
              {currentStep > step.number ? (
                <Check style={{ width: 14, height: 14 }} strokeWidth={3} />
              ) : (
                step.number
              )}
            </Box>
            {/* Step Label */}
            <Typography
              sx={{
                mt: { xs: 0.5, sm: 1 },
                textAlign: "center",
                fontSize: { xs: "10px", sm: "0.875rem" },
                fontWeight: 500,
                color: currentStep >= step.number ? "#4D8AFF" : "#9ca3af",
              }}
            >
              {step.label}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}
