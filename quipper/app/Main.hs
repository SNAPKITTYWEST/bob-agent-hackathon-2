-- quipper/app/Main.hs
-- Entry point for the quipper-examples executable.
-- Runs all three example circuits and prints JSON to stdout.

module Main where

import Quipper.Examples (runExamples)

main :: IO ()
main = runExamples
