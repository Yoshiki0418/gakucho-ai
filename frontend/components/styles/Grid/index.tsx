"use client";
import styled from "styled-components";
import Box from "../Box";

type GridProps = {
  $gridTemplateColumns?: string;
  $gridTemplateRows?: string;
  $gridTemplateAreas?: string;
  $gridAutoColumns?: string;
  $gridAutoRows?: string;
  $gridAutoFlow?: string;
  $justifyItems?: string;
  $alignItems?: string;
  $placeItems?: string;
  $justifyContent?: string;
  $alignContent?: string;
  $placeContent?: string;
};

const Grid = styled(Box) <GridProps>`
  display: grid;
  grid-template-columns: ${({ $gridTemplateColumns }) => $gridTemplateColumns};
  grid-template-rows: ${({ $gridTemplateRows }) => $gridTemplateRows};
  grid-template-areas: ${({ $gridTemplateAreas }) => $gridTemplateAreas};
  grid-auto-columns: ${({ $gridAutoColumns }) => $gridAutoColumns};
  grid-auto-rows: ${({ $gridAutoRows }) => $gridAutoRows};
  grid-auto-flow: ${({ $gridAutoFlow }) => $gridAutoFlow};
  justify-items: ${({ $justifyItems }) => $justifyItems};
  align-items: ${({ $alignItems }) => $alignItems};
  place-items: ${({ $placeItems }) => $placeItems};
  justify-content: ${({ $justifyContent }) => $justifyContent};
  align-content: ${({ $alignContent }) => $alignContent};
  place-content: ${({ $placeContent }) => $placeContent};
`;


export default Grid
