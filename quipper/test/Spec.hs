-- quipper/test/Spec.hs
-- HSpec auto-discovery entry point.
-- Run with: cabal test quipper-spec

import Test.Hspec
import QuipperSpec (spec)

main :: IO ()
main = hspec spec
