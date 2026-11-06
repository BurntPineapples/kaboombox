# Disclaimer, Safety Notice and Limitation of Liability

**Read this entire document before using anything in this repository.
If you do not agree with all of it, do not use, build, copy or modify this project.**

## 1. What this is

This repository contains a personal hobby project: firmware, circuit board designs,
3D-printable enclosure designs and documentation for a wireless remote-firing
controller. It is published **for educational and informational purposes only**.

It is **not** a commercial product. It is **not** certified, listed, tested or approved
by any standards body, regulator, testing laboratory, insurer or authority (for example
UL, CE, FCC, ATF, NFPA, BAM, HSE or any local equivalent). It has **not** been
independently reviewed for safety. It is **not** professional pyrotechnic equipment and
must not be used as a substitute for it.

## 1a. Work in progress: nothing here is final

This project is under active development and is revised often. The PCB designs, gerber
files, 3D models, printed-part files, firmware, wiring diagrams and documentation are
**not final**. They may contain errors, may not match each other, and may change at any
time without notice. Designs published here have not necessarily been built, tested or
verified in their current form.

Ordering PCBs, printing parts or building anything from this repository is done
**entirely at your own risk and expense**. The author(s) are not responsible for wasted
money, materials or time, for parts that do not fit or do not work, or for any harm caused
by building or using an unfinished design.

## 2. Pyrotechnics are dangerous

Fireworks, igniters, e-matches, steel wool and every other pyrotechnic or ignition device
can cause **death, serious injury, blindness, hearing loss, burns, fire and property
damage**. Electrical firing systems add further risks, including but not limited to:

- unexpected or premature ignition caused by wiring faults, short circuits, stray voltage,
  static discharge, radio interference, component failure, low or failing batteries,
  moisture, firmware bugs or user error;
- failure to fire, followed by a delayed ignition ("hang fire") while someone approaches;
- relay contacts welding closed, or relays changing state on power-up or brown-out;
- loss of the wireless link, interference from other 2.4 GHz devices, or range far lower
  than expected;
- fire caused by the 12 V battery, wiring or igniter.

**Never** approach a device that failed to fire until the firing battery is disconnected,
the fuse is removed and a safe waiting period has passed. Never stand over or near a
connected firework. Keep spectators at the distance required by law and by the product
manufacturer.

## 3. Wireless link limitations

The two units talk over ESP-NOW. Packets are **not encrypted or authenticated**. The
firmware ignores packets from MAC addresses other than the paired unit, but MAC addresses
can be spoofed, so this filtering is **not** a security measure. Do not rely on the
wireless link for safety. The physical arming key and the removable firing fuse are the
safety devices; the software only adds convenience checks on top of them.

## 4. Safety features must never be bypassed

The design includes:

- a **removable fuse** in the 12 V firing circuit (no fuse = no firing power);
- a **3-position arming key** that must be seen in DISARMED after power-up before it can arm,
  and that opens every relay when turned to DISARMED;
- a **heartbeat auto-disarm**: the field unit refuses to fire and cuts firing pulses if it
  has not heard an ARMED heartbeat within 1.5 seconds;
- relays forced off as the first action at boot, and a hard cap on pulse length.

**Do not remove, bypass, jumper, disable or weaken any of these.** Doing so makes the system
far more dangerous. These features reduce some risks; they do **not** make the system safe,
and they can fail.

## 5. Your responsibility

By using anything in this repository you accept that **you alone** are responsible for:

- complying with **all laws, regulations, permits, licences, insurance requirements and
  local rules** that apply to you, including laws on fireworks, explosives, pyrotechnic
  firing systems, radio transmitters and outdoor burning. In many places using or building
  such a system requires a licence or is prohibited. Check before you build;
- having the training, competence and supervision needed to work safely with electricity,
  batteries and pyrotechnics;
- inspecting, testing and verifying every part of your build, including testing with
  **no pyrotechnics connected** (for example with a test lamp or LED in place of the igniter)
  before every use;
- the safety of yourself, every person present, animals and property.

The documentation may contain errors, omissions or outdated information. Component
values, pin assignments and board layouts may be wrong. Verify everything yourself.

## 6. No warranty

EVERYTHING IN THIS REPOSITORY — SOFTWARE, FIRMWARE, HARDWARE DESIGNS, PCB FILES, 3D MODELS,
DOCUMENTATION AND ANY PRODUCT BUILT FROM THEM — IS PROVIDED **"AS IS" AND "AS AVAILABLE",
WITHOUT WARRANTY OF ANY KIND**, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, SAFETY, RELIABILITY, ACCURACY AND
NON-INFRINGEMENT. THE ENTIRE RISK AS TO THE QUALITY, PERFORMANCE AND SAFETY OF ANYTHING YOU
BUILD OR USE IS WITH YOU.

## 7. Limitation of liability

TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, IN NO EVENT SHALL THE AUTHOR(S),
CONTRIBUTORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY DEATH, PERSONAL INJURY, PROPERTY DAMAGE,
FIRE, LOSS, FINE, PENALTY, LEGAL ACTION, OR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, PUNITIVE OR CONSEQUENTIAL DAMAGES OF ANY KIND, HOWEVER CAUSED AND ON ANY THEORY
OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY OR TORT (INCLUDING NEGLIGENCE OR
OTHERWISE), ARISING IN ANY WAY OUT OF THE USE OF, INABILITY TO USE, BUILDING, MODIFYING OR
DISTRIBUTING ANYTHING IN THIS REPOSITORY, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

You agree to **indemnify and hold harmless** the author(s) and contributors from any claim,
demand, loss or damage, including legal fees, made by you or any third party arising out of
your use of this repository or anything built from it.

## 8. No advice, no support, no endorsement

Nothing here is professional, engineering, legal or safety advice. No support, maintenance
or updates are promised. Mention of any product, brand or vendor (for example ELEGOO,
Espressif, KiCad, JLCPCB, Autodesk) is for identification only and does not imply
endorsement by or affiliation with them.

## 9. Licences

The licences in [`LICENSE`](LICENSE) (MIT) and [`LICENSE-HARDWARE`](LICENSE-HARDWARE)
(CERN-OHL-P v2) also contain disclaimers of warranty and limitations of liability, which
apply in addition to this document.

If any part of this disclaimer is held unenforceable, the remaining parts stay in effect.
