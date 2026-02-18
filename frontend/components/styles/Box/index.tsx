"use client";
import styled from "styled-components"

export type BoxProps = {
    $position?: string;
    $color?: string
    $backgroundColor?: string
    $width?: string
    $height?: string
    $maxWidth?: string
    $maxHeight?: string
    $minWidth?: string
    $minHeight?: string
    $display?: string
    $border?: string
    $overflow?: string
    $margin?: string
    $marginTop?: string
    $marginRight?: string
    $marginBottom?: string
    $marginLeft?: string
    $padding?: string
    $paddingTop?: string
    $paddingRight?: string
    $paddingBottom?: string
    $justifyContent?: string;
    $alignItems?: string;
    $paddingLeft?: string
    $borderButton?: string
    $borderRadius?: string
    $zIndex?: string;
    $boxShadow?: string;
    $textAlign?: string;
    $hover_backgroundColor?: string;
}

const Box = styled.div<BoxProps>`
    position: ${({ $position }) => $position};
    color:${({ $color }) => $color};
    background-color:${({ $backgroundColor }) => $backgroundColor};
    width:${({ $width }) => $width};
    height:${({ $height }) => $height};
    max-width:${({ $maxWidth }) => $maxWidth};
    max-height:${({ $maxHeight }) => $maxHeight};
    min-width:${({ $minWidth }) => $minWidth};
    min-height:${({ $minHeight }) => $minHeight};
    display:${({ $display }) => $display};
    border:${({ $border }) => $border};
    border-radius:${({ $borderRadius }) => $borderRadius};
    overflow:${({ $overflow }) => $overflow};
    margin:${({ $margin }) => $margin};
    margin-top:${({ $marginTop }) => $marginTop};
    margin-right:${({ $marginRight }) => $marginRight};
    margin-bottom:${({ $marginBottom }) => $marginBottom};
    margin-left:${({ $marginLeft }) => $marginLeft};
    padding:${({ $padding }) => $padding};
    padding-top:${({ $paddingTop }) => $paddingTop};
    padding-right:${({ $paddingRight }) => $paddingRight};
    padding-bottom:${({ $paddingBottom }) => $paddingBottom};
    padding-left:${({ $paddingLeft }) => $paddingLeft};
    border-bottom:${({ $borderButton }) => $borderButton};
    z-index: ${({ $zIndex }) => $zIndex};
    box-shadow: ${({ $boxShadow }) => $boxShadow};
    text-align: ${({ $textAlign }) => $textAlign};
    justify-content: ${({ $justifyContent }) => $justifyContent};
    align-items: ${({ $alignItems }) => $alignItems};
    &:hover {
        background-color: ${({ $hover_backgroundColor }) => $hover_backgroundColor};
    }
`

export default Box
