"""Windows Authenticode verification without spawning child processes.

Spawning ``powershell Get-AuthenticodeSignature`` at update time is a
behavioural trigger for Defender's ML heuristics (Wacatac.H!ml family:
downloader that shells out to run system commands). This module performs the
same two checks — trusted embedded signature plus optional publisher-subject
substring — purely in-process via WinVerifyTrust + crypt32.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path


def _win_api():  # noqa: ANN202
    wintrust = ctypes.WinDLL("wintrust")
    crypt32 = ctypes.WinDLL("crypt32")

    class _GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        ]

    class _WINTRUST_FILE_INFO(ctypes.Structure):
        _fields_ = [
            ("cbStruct", wintypes.DWORD),
            ("pcwszFilePath", wintypes.LPCWSTR),
            ("hFile", wintypes.HANDLE),
            ("pgKnownSubject", ctypes.POINTER(_GUID)),
        ]

    class _WINTRUST_DATA(ctypes.Structure):
        _fields_ = [
            ("cbStruct", wintypes.DWORD),
            ("pPolicyCallbackData", ctypes.c_void_p),
            ("pSIPClientData", ctypes.c_void_p),
            ("dwUIChoice", wintypes.DWORD),
            ("fdwRevocationChecks", wintypes.DWORD),
            ("dwUnionChoice", wintypes.DWORD),
            ("pFile", ctypes.POINTER(_WINTRUST_FILE_INFO)),
            ("dwStateAction", wintypes.DWORD),
            ("hWVTStateData", wintypes.HANDLE),
            ("pwszURLReference", wintypes.LPCWSTR),
            ("dwProvFlags", wintypes.DWORD),
            ("dwUIContext", wintypes.DWORD),
            ("pSignatureSettings", ctypes.c_void_p),
        ]

    verify_action = _GUID(
        0x00AAC56B,
        0xCD44,
        0x11D0,
        (wintypes.BYTE * 8)(0x8C, 0xC2, 0x00, 0xC0, 0xCF, 0xC1, 0x64, 0xC5),
    )
    return wintrust, crypt32, _GUID, _WINTRUST_FILE_INFO, _WINTRUST_DATA, verify_action


def _trust_is_valid(path: str) -> bool:
    wintrust, _, _, _FILE_INFO, _DATA, action = _win_api()
    file_info = _FILE_INFO(
        cbStruct=ctypes.sizeof(_FILE_INFO),
        pcwszFilePath=path,
        hFile=None,
        pgKnownSubject=None,
    )
    data = _DATA()
    data.cbStruct = ctypes.sizeof(_DATA)
    data.dwUIChoice = 2  # WTD_UI_NONE
    data.fdwRevocationChecks = 0  # WTD_REVOKE_NONE
    data.dwUnionChoice = 1  # WTD_CHOICE_FILE
    data.pFile = ctypes.pointer(file_info)
    data.dwStateAction = 1  # WTD_STATEACTION_VERIFY
    data.dwUIContext = 0  # WTD_UICONTEXT_EXECUTE
    try:
        wintrust.WinVerifyTrust.argtypes = [wintypes.HWND, ctypes.c_void_p, ctypes.c_void_p]
        wintrust.WinVerifyTrust.restype = wintypes.LONG
        status = wintrust.WinVerifyTrust(None, ctypes.byref(action), ctypes.byref(data))
    finally:
        try:
            data.dwStateAction = 2  # WTD_STATEACTION_CLOSE
            wintrust.WinVerifyTrust(None, ctypes.byref(action), ctypes.byref(data))
        except Exception:
            pass
    return int(status) == 0


def _signer_subject(path: str) -> str | None:
    """Return the signing certificate's display subject, or None on failure."""
    _, crypt32, _, _, _, _ = _win_api()
    encoding = wintypes.DWORD()
    content_type = wintypes.DWORD()
    format_type = wintypes.DWORD()
    store = wintypes.HANDLE()
    msg = wintypes.HANDLE()
    try:
        ok = crypt32.CryptQueryObject(
            wintypes.DWORD(1),  # CERT_QUERY_OBJECT_FILE
            wintypes.LPCWSTR(path),
            wintypes.DWORD(0x3FFF),  # content: any
            wintypes.DWORD(0x3FFF),  # format: any
            wintypes.DWORD(0),
            ctypes.byref(encoding),
            ctypes.byref(content_type),
            ctypes.byref(format_type),
            ctypes.byref(store),
            ctypes.byref(msg),
            None,
        )
    except Exception:
        return None
    if not ok or not store or not msg:
        return None
    try:
        crypt32.CryptMsgGetParam.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            ctypes.POINTER(wintypes.DWORD),
        ]
        crypt32.CryptMsgGetParam.restype = wintypes.BOOL
        size = wintypes.DWORD(0)
        # 7 == CMSG_SIGNER_CERT_INFO_PARAM: CERT_INFO of the first signer.
        if not crypt32.CryptMsgGetParam(msg, 7, 0, None, ctypes.byref(size)):
            return None
        buf = ctypes.create_string_buffer(size.value)
        if not crypt32.CryptMsgGetParam(msg, 7, 0, buf, ctypes.byref(size)):
            return None
        crypt32.CertFindCertificateInStore.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        crypt32.CertFindCertificateInStore.restype = ctypes.c_void_p
        cert = crypt32.CertFindCertificateInStore(
            store,
            0x00010001,  # X509_ASN_ENCODING | PKCS7_ASN_ENCODING
            0,
            0x000B0000,  # CERT_FIND_SUBJECT_CERT (issuer + serial match)
            buf,
            None,
        )
        if not cert:
            return None
        try:
            crypt32.CertGetNameStringW.argtypes = [
                ctypes.c_void_p,
                wintypes.DWORD,
                wintypes.DWORD,
                ctypes.c_void_p,
                wintypes.LPWSTR,
                wintypes.DWORD,
            ]
            crypt32.CertGetNameStringW.restype = wintypes.DWORD
            length = crypt32.CertGetNameStringW(cert, 4, 0, None, None, 0)
            if length <= 1:
                return None
            out = ctypes.create_unicode_buffer(length)
            if crypt32.CertGetNameStringW(cert, 4, 0, None, out, length) <= 1:
                return None
            return out.value
        finally:
            try:
                crypt32.CertFreeCertificateContext(cert)
            except Exception:
                pass
    finally:
        for closer, handle in (
            (getattr(crypt32, "CertCloseStore", None), store),
            (getattr(crypt32, "CryptMsgClose", None), msg),
        ):
            try:
                if closer is not None and handle:
                    closer(handle, 0) if closer.__name__ == "CertCloseStore" else closer(handle)
            except Exception:
                pass
    return None


def verify_windows_signature(path: str | Path, expected_publisher: str = "") -> bool:
    """Return True when *path* carries a trusted Authenticode signature.

    Non-Windows platforms return True (nothing to verify). When
    *expected_publisher* is non-empty, the signer subject must additionally
    contain it (case-insensitive), mirroring the old PowerShell check.
    Failures are fail-closed (False) and never spawn a subprocess.
    """
    if not sys.platform.startswith("win"):
        return True
    target = str(Path(path))
    try:
        if not _trust_is_valid(target):
            return False
    except Exception:
        return False
    want = (expected_publisher or "").strip()
    if not want:
        return True
    try:
        subject = _signer_subject(target)
    except Exception:
        return False
    if not subject:
        return False
    return want.lower() in subject.lower()
