'use client'
import styled from "styled-components"

type UserIconProps = {
    $size?: string
    $borderRadius?: string
    $backgroundColor?: string
    $display?: string
    $fontSize?: string
    $color?: string
    $border?: string
}

const UserIcon = styled.div<UserIconProps>`
    width: ${({ $size }) => $size || "80px"};
    height: ${({ $size }) => $size || "80px"};
    border-radius: ${({ $borderRadius }) => $borderRadius || "50%"};
    background-color: ${({ $backgroundColor }) => $backgroundColor || "#D9D9D9"};
    display:${({ $display }) => $display || "flex"};
    font-size:${({ $fontSize }) => $fontSize || "1rem"};
    color:${({ $color }) => $color || "white"};
    border: ${({ $border }) => $border || "none"};
    align-items: center;
    justify-content: center;
`

export default UserIcon
