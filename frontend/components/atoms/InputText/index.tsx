'use client'
import styled, { css } from "styled-components"
import React, { forwardRef } from "react";

type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
    $color?: string
    $backgroundColor?: string
    $width?: string
    $height?: string
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
    $paddingLeft?: string
    $borderButton?: string
    $borderRadius?: string
    $variants?: 'auth' | 'serch' | 'chat'
    onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void;
    placeholder?: string
    $textAlign?: string
    $isError?: boolean;
    $background: string;
}

const InputCSS = styled.input<InputProps>`
    ${({ $variants, theme }) => {
        switch ($variants) {
            case "auth":
                return css`
                    width: 21.25rem;
                    height: 3.125rem;
                    font-size: ${theme.fontSize.Small};
                    padding: 0.5rem 1rem;
                    border: 2px solid #CCCCCC;
                `
            case "serch":
                return css`
                    width: 46.635rem;
                    height: 3rem;
                    font-size: ${theme.fontSize.Small};
                `
            case "chat":
                return css`
                    width: 30.375rem;
                    height: 2.35rem;
                    font-size: ${theme.fontSize.Small};
                    padding: 1.25rem 1.0rem;
                    color: #484B4A;
                `
        }
    }};
    color:${({ color }) => color};
    background-color:${({ $backgroundColor }) => $backgroundColor || "#FFFFFF"};
    width:${({ $width }) => $width};
    height:${({ $height }) => $height};
    min-width:${({ $minWidth }) => $minWidth};
    min-height:${({ $minHeight }) => $minHeight};
    display:${({ $display }) => $display};
    border:${({ $border }) => $border};
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
    text-align:${({ $textAlign }) => $textAlign};
    border-color: ${({ $isError }) => ($isError ? "#FF0000" : "#CCCCCC")};
    background: ${({ $background }) => $background};
    &:focus {
        outline: none;
        border-color: ${({ $isError }) => ($isError ? "#FF6666" : "#6666FF")};
    }
`

const Input = forwardRef<HTMLInputElement, InputProps>(
    (props, ref) => {
        return <InputCSS ref={ref} {...props} />
    })

export default Input
